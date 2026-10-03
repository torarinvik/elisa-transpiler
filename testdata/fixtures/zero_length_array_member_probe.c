struct PacketWithZeroLengthBytes {
    unsigned long length;
    unsigned char data[0];
};

unsigned char read_packet_byte(struct PacketWithZeroLengthBytes *packet, unsigned long index) {
    return packet->data[index];
}
