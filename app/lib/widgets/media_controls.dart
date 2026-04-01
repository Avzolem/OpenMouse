// app/lib/widgets/media_controls.dart
import 'package:flutter/material.dart';
import 'package:openmouse/models/packet.dart';
import 'package:openmouse/services/connection_service.dart';

class MediaControls extends StatelessWidget {
  final ConnectionService connectionService;

  const MediaControls({super.key, required this.connectionService});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Playback controls
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _MediaButton(
                icon: Icons.skip_previous_rounded,
                size: 56,
                onTap: () => connectionService.sendTcp(Packet.mediaPrev()),
              ),
              _MediaButton(
                icon: Icons.play_arrow_rounded,
                size: 80,
                primary: true,
                onTap: () => connectionService.sendTcp(Packet.mediaPlayPause()),
              ),
              _MediaButton(
                icon: Icons.skip_next_rounded,
                size: 56,
                onTap: () => connectionService.sendTcp(Packet.mediaNext()),
              ),
            ],
          ),
          const SizedBox(height: 48),
          // Volume controls
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _MediaButton(
                icon: Icons.volume_down_rounded,
                size: 56,
                onTap: () => connectionService.sendTcp(Packet.volumeDown()),
              ),
              _MediaButton(
                icon: Icons.volume_off_rounded,
                size: 56,
                onTap: () => connectionService.sendTcp(Packet.volumeMute()),
              ),
              _MediaButton(
                icon: Icons.volume_up_rounded,
                size: 56,
                onTap: () => connectionService.sendTcp(Packet.volumeUp()),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MediaButton extends StatelessWidget {
  final IconData icon;
  final double size;
  final bool primary;
  final VoidCallback onTap;

  const _MediaButton({
    required this.icon,
    required this.size,
    this.primary = false,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: primary ? Colors.green[400] : const Color(0xFF16213E),
          shape: BoxShape.circle,
        ),
        child: Icon(
          icon,
          color: primary ? Colors.white : Colors.grey[300],
          size: size * 0.5,
        ),
      ),
    );
  }
}
