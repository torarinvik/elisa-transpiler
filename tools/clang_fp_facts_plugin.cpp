// Narrow Clang semantic-fact bridge for source-scoped floating-point options.
// Translation policy and lowering remain in Elisa; this plugin only serializes
// Clang's already-resolved FPOptions for expressions that differ from the
// translation-unit defaults.

#include "clang/AST/ASTConsumer.h"
#include "clang/AST/ASTContext.h"
#include "clang/AST/Expr.h"
#include "clang/AST/RecursiveASTVisitor.h"
#include "clang/Basic/Diagnostic.h"
#include "clang/Basic/FileEntry.h"
#include "clang/Basic/Version.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Frontend/FrontendPluginRegistry.h"
#include "clang/Frontend/FrontendActions.h"
#include "clang/Lex/Lexer.h"
#include "llvm/Support/FileSystem.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/MemoryBuffer.h"
#include "llvm/Support/raw_ostream.h"

#include <cstdint>
#include <memory>
#include <string>
#include <system_error>
#include <utility>
#include <vector>

namespace {

constexpr llvm::StringLiteral PluginName = "elisa-fp-facts";
constexpr llvm::StringLiteral SchemaName = "elisa-clang-fp-facts-v1";
constexpr uint64_t DefaultMaxRecords = 250000;
constexpr uint64_t DefaultMaxPayloadBytes = 32 * 1024 * 1024;

bool parsePositiveLimit(llvm::StringRef Text, uint64_t HardMaximum,
                        uint64_t &Value) {
  if (Text.getAsInteger(10, Value) || Value == 0 || Value > HardMaximum)
    return false;
  return true;
}

bool hasFloatingType(clang::QualType Type) {
  return !Type.isNull() &&
         (Type->isRealFloatingType() || Type->isAnyComplexType());
}

bool hasFloatingPointSemantics(const clang::Expr *Expression) {
  if (Expression == nullptr)
    return false;
  if (hasFloatingType(Expression->getType()))
    return true;
  if (const auto *Binary = llvm::dyn_cast<clang::BinaryOperator>(Expression))
    return hasFloatingType(Binary->getLHS()->getType()) ||
           hasFloatingType(Binary->getRHS()->getType());
  if (const auto *Unary = llvm::dyn_cast<clang::UnaryOperator>(Expression))
    return hasFloatingType(Unary->getSubExpr()->getType());
  if (const auto *Cast = llvm::dyn_cast<clang::CastExpr>(Expression))
    return hasFloatingType(Cast->getSubExpr()->getType());
  if (const auto *Call = llvm::dyn_cast<clang::CallExpr>(Expression)) {
    for (const clang::Expr *Argument : Call->arguments())
      if (hasFloatingType(Argument->getType()))
        return true;
  }
  return false;
}

std::string physicalFileName(clang::SourceManager &SM,
                             clang::SourceLocation Location) {
  clang::SourceLocation FileLocation = SM.getFileLoc(Location);
  if (FileLocation.isInvalid())
    return {};
  const clang::FileEntry *Entry = SM.getFileEntryForID(SM.getFileID(FileLocation));
  if (Entry != nullptr) {
    llvm::StringRef RealPath = Entry->tryGetRealPathName();
    if (!RealPath.empty())
      return RealPath.str();
    return Entry->getName().str();
  }
  return SM.getBufferName(FileLocation).str();
}

llvm::json::Object locationObject(clang::SourceManager &SM,
                                  clang::SourceLocation Location) {
  llvm::json::Object Result;
  if (Location.isInvalid())
    return Result;

  clang::SourceLocation FileLocation = SM.getFileLoc(Location);
  if (FileLocation.isInvalid())
    return Result;

  clang::FileID FileID = SM.getFileID(FileLocation);
  std::string File = physicalFileName(SM, FileLocation);
  if (!File.empty())
    Result["file"] = std::move(File);
  unsigned Offset = SM.getFileOffset(FileLocation);
  Result["offset"] = static_cast<int64_t>(Offset);
  Result["line"] = static_cast<int64_t>(SM.getLineNumber(FileID, Offset));
  Result["column"] = static_cast<int64_t>(SM.getColumnNumber(FileID, Offset));
  clang::PresumedLoc Presumed = SM.getPresumedLoc(Location);
  if (Presumed.isValid()) {
    Result["presumed_line"] = static_cast<int64_t>(Presumed.getLine());
    Result["presumed_column"] =
        static_cast<int64_t>(Presumed.getColumn());
  }
  return Result;
}

llvm::json::Object sourceRangeObject(clang::ASTContext &Context,
                                     clang::SourceRange Range) {
  llvm::json::Object Result;
  clang::SourceManager &SM = Context.getSourceManager();
  const clang::LangOptions &LangOpts = Context.getLangOpts();

  Result["begin"] = locationObject(SM, Range.getBegin());
  Result["end"] = locationObject(SM, Range.getEnd());
  if (Range.getEnd().isValid()) {
    unsigned TokenLength = clang::Lexer::MeasureTokenLength(
        Range.getEnd(), SM, LangOpts);
    Result["end_token_length"] = static_cast<int64_t>(TokenLength);
  }

  clang::SourceLocation SpellingBegin = SM.getSpellingLoc(Range.getBegin());
  clang::SourceLocation ExpansionBegin = SM.getExpansionLoc(Range.getBegin());
  clang::SourceLocation SpellingEnd = SM.getSpellingLoc(Range.getEnd());
  clang::SourceLocation ExpansionEnd = SM.getExpansionLoc(Range.getEnd());
  if (SpellingBegin.isValid() && ExpansionBegin.isValid() &&
      SpellingBegin != ExpansionBegin) {
    Result["spelling_begin"] = locationObject(SM, SpellingBegin);
    Result["expansion_begin"] = locationObject(SM, ExpansionBegin);
  }
  if (SpellingEnd.isValid() && ExpansionEnd.isValid() &&
      SpellingEnd != ExpansionEnd) {
    Result["spelling_end"] = locationObject(SM, SpellingEnd);
    Result["expansion_end"] = locationObject(SM, ExpansionEnd);
  }
  return Result;
}

llvm::json::Object fpOptionsObject(const clang::FPOptions &Options) {
  llvm::json::Object Result;
  Result["contract_mode"] =
      static_cast<int64_t>(Options.getFPContractMode());
  Result["rounding_math"] = Options.getRoundingMath();
  Result["constant_rounding_mode"] =
      static_cast<int64_t>(Options.getConstRoundingMode());
  Result["exception_mode"] =
      static_cast<int64_t>(Options.getSpecifiedExceptionMode());
  Result["fenv_access"] = Options.getAllowFEnvAccess();
  Result["reassociate"] = Options.getAllowFPReassociate();
  Result["no_honor_nans"] = Options.getNoHonorNaNs();
  Result["no_honor_infinities"] = Options.getNoHonorInfs();
  Result["no_signed_zero"] = Options.getNoSignedZero();
  Result["reciprocal"] = Options.getAllowReciprocal();
  Result["approximate_functions"] = Options.getAllowApproxFunc();
  Result["evaluation_method"] =
      static_cast<int64_t>(Options.getFPEvalMethod());
  Result["float16_excess_precision"] =
      static_cast<int64_t>(Options.getFloat16ExcessPrecision());
  Result["bfloat16_excess_precision"] =
      static_cast<int64_t>(Options.getBFloat16ExcessPrecision());
  Result["math_errno"] = Options.getMathErrno();
  Result["complex_range"] =
      static_cast<int64_t>(Options.getComplexRange());
  return Result;
}

class FPFactVisitor final
    : public clang::RecursiveASTVisitor<FPFactVisitor> {
public:
  FPFactVisitor(clang::ASTContext &Context, uint64_t MaxRecords,
                uint64_t MaxPayloadBytes)
      : Context(Context),
        TranslationUnitDefaults(Context.getLangOpts()),
        MaxRecords(MaxRecords), MaxPayloadBytes(MaxPayloadBytes) {}

  bool VisitExpr(clang::Expr *Expression) {
    if (Expression == nullptr || Expression->getType().isNull())
      return true;
    clang::QualType Type = Expression->getType();
    if (!hasFloatingPointSemantics(Expression))
      return true;

    clang::FPOptions Effective =
        Expression->getFPFeaturesInEffect(Context.getLangOpts());
    if (Effective == TranslationUnitDefaults)
      return true;
    if (Records.size() >= MaxRecords) {
      LimitExceeded = "record-count";
      return false;
    }

    llvm::json::Object Record;
    Record["kind"] = Expression->getStmtClassName();
    Record["type"] = Type.getAsString();
    Record["range"] = sourceRangeObject(Context, Expression->getSourceRange());
    Record["fp"] = fpOptionsObject(Effective);

    // Bound the retained JSON objects by their actual compact serialized
    // payload. The record-count ceiling also bounds per-object bookkeeping.
    std::string SerializedRecord;
    llvm::raw_string_ostream SerializedStream(SerializedRecord);
    llvm::json::OStream SerializedJSON(SerializedStream);
    llvm::json::Object RecordForSize = Record;
    SerializedJSON.value(llvm::json::Value(std::move(RecordForSize)));
    uint64_t RecordBytes = SerializedRecord.size() + 1;
    if (RecordBytes > MaxPayloadBytes ||
        PayloadBytes > MaxPayloadBytes - RecordBytes) {
      LimitExceeded = "serialized-payload-bytes";
      return false;
    }
    PayloadBytes += RecordBytes;
    Records.emplace_back(std::move(Record));
    return true;
  }

  llvm::json::Array takeRecords() { return std::move(Records); }
  const std::string &limitExceeded() const { return LimitExceeded; }

private:
  clang::ASTContext &Context;
  clang::FPOptions TranslationUnitDefaults;
  uint64_t MaxRecords;
  uint64_t MaxPayloadBytes;
  uint64_t PayloadBytes = 0;
  std::string LimitExceeded;
  llvm::json::Array Records;
};

class FPFactConsumer final : public clang::ASTConsumer {
public:
  FPFactConsumer(clang::CompilerInstance &Compiler, std::string OutputPath,
                 uint64_t MaxRecords, uint64_t MaxPayloadBytes)
      : Compiler(Compiler), OutputPath(std::move(OutputPath)),
        MaxRecords(MaxRecords), MaxPayloadBytes(MaxPayloadBytes) {}

  void HandleTranslationUnit(clang::ASTContext &Context) override {
    FPFactVisitor Visitor(Context, MaxRecords, MaxPayloadBytes);
    Visitor.TraverseDecl(Context.getTranslationUnitDecl());
    if (!Visitor.limitExceeded().empty()) {
      unsigned Diagnostic = Compiler.getDiagnostics().getCustomDiagID(
          clang::DiagnosticsEngine::Error,
          "Elisa FP facts exceeded the configured %0 limit; no facts file was written");
      Compiler.getDiagnostics().Report(Diagnostic) << Visitor.limitExceeded();
      return;
    }

    llvm::json::Object Root;
    Root["schema"] = SchemaName;
    Root["clang_version"] = clang::getClangFullVersion();
    Root["record_policy"] = "effective-options-when-nondefault";
    Root["records_complete"] = true;
    llvm::json::Object Limits;
    Limits["max_records"] = static_cast<int64_t>(MaxRecords);
    Limits["max_serialized_payload_bytes"] =
        static_cast<int64_t>(MaxPayloadBytes);
    Root["limits"] = std::move(Limits);
    Root["default_fp"] =
        fpOptionsObject(clang::FPOptions(Context.getLangOpts()));
    clang::SourceManager &SM = Context.getSourceManager();
    clang::SourceLocation MainLocation =
        SM.getLocForStartOfFile(SM.getMainFileID());
    Root["translation_unit"] = physicalFileName(SM, MainLocation);
    Root["records"] = Visitor.takeRecords();

    std::error_code Error;
    llvm::raw_fd_ostream Output(OutputPath, Error,
                                llvm::sys::fs::OF_TextWithCRLF);
    if (Error) {
      unsigned Diagnostic = Compiler.getDiagnostics().getCustomDiagID(
          clang::DiagnosticsEngine::Error,
          "could not write Elisa FP facts file '%0': %1");
      Compiler.getDiagnostics().Report(Diagnostic)
          << OutputPath << Error.message();
      return;
    }

    llvm::json::OStream JSON(Output);
    JSON.value(llvm::json::Value(std::move(Root)));
    Output << '\n';
    Output.flush();
    if (Output.has_error()) {
      unsigned Diagnostic = Compiler.getDiagnostics().getCustomDiagID(
          clang::DiagnosticsEngine::Error,
          "failed while writing Elisa FP facts file '%0'");
      Compiler.getDiagnostics().Report(Diagnostic) << OutputPath;
      Output.clear_error();
    }
  }

private:
  clang::CompilerInstance &Compiler;
  std::string OutputPath;
  uint64_t MaxRecords;
  uint64_t MaxPayloadBytes;
};

class FPFactAction final : public clang::PluginASTAction {
public:
  bool ParseArgs(const clang::CompilerInstance &,
                 const std::vector<std::string> &Args) override {
    bool HasOutput = false;
    for (size_t Index = 0; Index < Args.size();) {
      if (Index + 1 >= Args.size())
        return false;
      llvm::StringRef Option(Args[Index]);
      llvm::StringRef Value(Args[Index + 1]);
      if (Option == "--output" && !HasOutput) {
        OutputPath = Value.str();
        HasOutput = !OutputPath.empty();
      } else if (Option == "--max-records") {
        if (!parsePositiveLimit(Value, DefaultMaxRecords, MaxRecords))
          return false;
      } else if (Option == "--max-output-bytes") {
        if (!parsePositiveLimit(Value, DefaultMaxPayloadBytes,
                                MaxPayloadBytes))
          return false;
      } else {
        return false;
      }
      Index += 2;
    }
    return HasOutput;
  }

  std::unique_ptr<clang::ASTConsumer>
  CreateASTConsumer(clang::CompilerInstance &Compiler,
                   llvm::StringRef) override {
    return std::make_unique<FPFactConsumer>(Compiler, OutputPath, MaxRecords,
                                            MaxPayloadBytes);
  }

  ActionType getActionType() override { return AddAfterMainAction; }

private:
  std::string OutputPath;
  uint64_t MaxRecords = DefaultMaxRecords;
  uint64_t MaxPayloadBytes = DefaultMaxPayloadBytes;
};

} // namespace

static clang::FrontendPluginRegistry::Add<FPFactAction>
    RegisterFPFactAction(PluginName, "emit effective scoped floating-point facts");
