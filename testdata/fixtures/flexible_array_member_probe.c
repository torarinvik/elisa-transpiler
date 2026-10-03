struct PacketWithFlexibleBytes {
    unsigned long length;
    unsigned char data[];
};

unsigned char read_packet_byte(struct PacketWithFlexibleBytes *packet, unsigned long index) {
    return packet->data[index];
}
