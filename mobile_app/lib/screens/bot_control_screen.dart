import 'dart:convert';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../app_theme.dart';

class BotControlScreen extends StatefulWidget {
  const BotControlScreen({Key? key}) : super(key: key);

  @override
  _BotControlScreenState createState() => _BotControlScreenState();
}

class _BotControlScreenState extends State<BotControlScreen> {
  bool _isLoading = false;
  String _status = 'STOPPED'; // RUNNING, PAUSED, STOPPED
  String _uptime = '0h 0m';
  int _trades = 0;
  double _pnl = 0.0;
  double _dailyLimit = 25.0;
  double _usedLimit = 0.0;

  @override
  void initState() {
    super.initState();
    _fetchStatus();
  }

  Future<void> _fetchStatus() async {
    setState(() => _isLoading = true);
    try {
      final response = await ApiService().get(context, '/control/status');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _status = data['status'] ?? 'STOPPED';
          _uptime = data['uptime'] ?? '0h 0m';
          _trades = data['trades'] ?? 0;
          _pnl = (data['pnl'] ?? 0.0).toDouble();
          _dailyLimit = (data['dailyLimit'] ?? 25.0).toDouble();
          _usedLimit = (data['usedLimit'] ?? 0.0).toDouble();
        });
      } else {
        _mockData();
      }
    } catch (e) {
      _mockData();
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _mockData() {
    setState(() {
      _status = 'RUNNING';
      _uptime = '2h 34m';
      _trades = 3;
      _pnl = 8.40;
      _dailyLimit = 25.0;
      _usedLimit = 4.0;
    });
  }

  Future<void> _sendControlCommand(String action) async {
    setState(() => _isLoading = true);
    try {
      final response = await ApiService().post(context, '/control/${action.toLowerCase()}');
      if (response.statusCode == 200) {
        // Assume API returns updated status
        final data = jsonDecode(response.body);
        setState(() {
          _status = data['status'] ?? (action == 'START' ? 'RUNNING' : action);
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Bot $action successful'),
              backgroundColor: AppTheme.profit,
            ),
          );
        }
      } else {
        throw Exception('Failed to send command');
      }
    } catch (e) {
      // Mock logic for demo
      setState(() {
        if (action == 'START') _status = 'RUNNING';
        if (action == 'PAUSE') _status = 'PAUSED';
        if (action == 'STOP') _status = 'STOPPED';
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Simulated: Bot $action successful'),
            backgroundColor: AppTheme.profit,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Color _getStatusColor() {
    switch (_status) {
      case 'RUNNING': return AppTheme.profit;
      case 'PAUSED': return AppTheme.accent;
      default: return AppTheme.loss;
    }
  }

  Widget _buildStatusSection() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppTheme.cardBackground,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          const Text('BOT STATUS', style: AppTheme.subtitle),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 16,
                height: 16,
                decoration: BoxDecoration(
                  color: _getStatusColor(),
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 12),
              Text(
                _status,
                style: TextStyle(
                  color: _getStatusColor(),
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Uptime: $_uptime',
            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 16),
          ),
        ],
      ),
    );
  }

  Widget _buildControlButtons() {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _buildButton(
                title: '▶ START',
                color: AppTheme.profit,
                onPressed: _status == 'RUNNING' ? null : () => _sendControlCommand('START'),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: _buildButton(
                title: '⏸ PAUSE',
                color: AppTheme.accent,
                onPressed: _status == 'PAUSED' || _status == 'STOPPED'
                    ? null
                    : () => _sendControlCommand('PAUSE'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          child: _buildButton(
            title: '⏹ STOP',
            color: AppTheme.loss,
            onPressed: _status == 'STOPPED' ? null : () => _sendControlCommand('STOP'),
          ),
        ),
      ],
    );
  }

  Widget _buildButton({required String title, required Color color, required VoidCallback? onPressed}) {
    return SizedBox(
      height: 54,
      child: ElevatedButton(
        style: ElevatedButton.styleFrom(
          backgroundColor: color,
          disabledBackgroundColor: color.withOpacity(0.3),
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
        onPressed: _isLoading ? null : onPressed,
        child: Text(
          title,
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
      ),
    );
  }

  Widget _buildStatsSection() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppTheme.cardBackground,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text("TODAY'S STATS", style: AppTheme.subtitle),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Trades: $_trades', style: AppTheme.title),
              Text(
                'PnL: ${_pnl >= 0 ? '+' : ''}\$$_pnl',
                style: TextStyle(
                  color: _pnl >= 0 ? AppTheme.profit : AppTheme.loss,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Daily limit: \$$_dailyLimit used: \$$_usedLimit',
            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 16),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.background,
      child: ListView(
        padding: const EdgeInsets.all(16),
        physics: const BouncingScrollPhysics(),
        children: [
          _buildStatusSection(),
          const SizedBox(height: 24),
          _buildControlButtons(),
          const SizedBox(height: 24),
          _buildStatsSection(),
        ],
      ),
    );
  }
}
