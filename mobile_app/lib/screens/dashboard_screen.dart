import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../app_theme.dart';
import '../api_config.dart';
import '../services/api_service.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  WebSocketChannel? _channel;
  Map<String, dynamic>? _data;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _fetchData();
    _connectWebSocket();
  }

  Map<String, dynamic> _normalizeData(Map<String, dynamic> raw) {
    // Extracts raw payload mapped onto guaranteed stable default values
    int pScore = 0;
    try {
      final s = raw['signalScore']?.toString() ?? raw['signal_score']?.toString();
      if (s != null && s.contains('/')) {
        pScore = int.tryParse(s.split('/')[0]) ?? 0;
      } else if (s != null) {
        pScore = int.tryParse(s) ?? 0;
      }
    } catch (_) {}

    String pLastUp = raw['lastUpdate']?.toString() ?? raw['last_update']?.toString() ?? 'N/A';
    if (pLastUp.contains('T')) {
      pLastUp = pLastUp.split('T').last.substring(0, 5);
    }

    return {
      'status': raw['status']?.toString().toUpperCase() ?? raw['bot_status']?.toString().toUpperCase() ?? 'UNKNOWN',
      'lastUpdate': pLastUp,
      'btcPrice': (raw['btcPrice'] as num?)?.toDouble() ?? (raw['btc_price'] as num?)?.toDouble() ?? 0.0,
      'btcChange': (raw['btcChange'] as num?)?.toDouble() ?? (raw['btc_change_24h'] as num?)?.toDouble() ?? 0.0,
      'portfolioUsdt': (raw['portfolioUsdt'] as num?)?.toDouble() ?? (raw['portfolio_value'] as num?)?.toDouble() ?? 0.0,
      'totalPnl': (raw['totalPnl'] as num?)?.toDouble() ?? (raw['total_pnl'] as num?)?.toDouble() ?? 0.0,
      'totalPnlPct': (raw['totalPnlPct'] as num?)?.toDouble() ?? (raw['total_pnl_pct'] as num?)?.toDouble() ?? 0.0,
      'openPnl': (raw['openPnl'] as num?)?.toDouble() ?? (raw['open_pnl'] as num?)?.toDouble() ?? 0.0,
      'regime': raw['regime']?.toString() ?? raw['overall_regime']?.toString() ?? 'SIDEWAYS',
      'signalScore': pScore,
      'rsi1h': (raw['rsi1h'] as num?)?.toDouble() ?? 50.0,
      'rsi4h': (raw['rsi4h'] as num?)?.toDouble() ?? 50.0,
      'rsi1d': (raw['rsi1d'] as num?)?.toDouble() ?? 50.0,
    };
  }

  Future<void> _fetchData() async {
    if (!mounted) return;
    setState(() => _isLoading = true);
    
    try {
      final statusResp = await ApiService().get(context, '/status');
      final portResp = await ApiService().get(context, '/portfolio');
      
      if (statusResp.statusCode == 200 && portResp.statusCode == 200) {
        final statusMap = jsonDecode(statusResp.body) as Map<String, dynamic>;
        final portMap = jsonDecode(portResp.body) as Map<String, dynamic>;
        
        // Merge the two maps logically giving precedence to whatever isn't null
        final mergedRaw = <String, dynamic>{...portMap, ...statusMap};
        
        if (mounted) {
          setState(() {
            _data = _normalizeData(mergedRaw);
          });
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString().replaceAll('Exception: ', '')), backgroundColor: AppTheme.loss)
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _connectWebSocket() {
    try {
      _channel?.sink.close();
      _channel = WebSocketChannel.connect(Uri.parse(WS_URL));
      _channel!.stream.listen(
        (message) {
          if (mounted) {
            try {
              final parsed = jsonDecode(message) as Map<String, dynamic>;
              setState(() {
                final currentRaw = _data != null ? Map<String, dynamic>.from(_data!) : <String, dynamic>{};
                final mergedRaw = <String, dynamic>{...currentRaw, ...parsed};
                _data = _normalizeData(mergedRaw);
              });
            } on FormatException catch (_) {
              // Silently drop ill-formatted websocket frames
            } catch (e) {
              print('WS Ext Error: $e');
            }
          }
        }, 
        onError: (error) {
          if (mounted) Future.delayed(const Duration(seconds: 5), _connectWebSocket);
        }, 
        onDone: () {
          if (mounted) Future.delayed(const Duration(seconds: 5), _connectWebSocket);
        }
      );
    } catch (e) {
      print('WS Connect Error: $e');
    }
  }

  Future<void> _sendControlCmd(String action) async {
    try {
      final response = await ApiService().post(context, '/control/$action');
      if (response.statusCode == 200) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Bot $action successful'), backgroundColor: AppTheme.profit)
          );
          Future.delayed(const Duration(seconds: 1), () {
            if (mounted) _fetchData();
          });
        }
      } else {
        throw Exception('Failed to $action bot');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString().replaceAll('Exception: ', '')), backgroundColor: AppTheme.loss)
        );
      }
    }
  }

  @override
  void dispose() {
    _channel?.sink.close();
    super.dispose();
  }

  Color _getRegimeColor(String regime) {
    if (regime.contains('UP')) return AppTheme.profit;
    if (regime.contains('DOWN')) return AppTheme.loss;
    return AppTheme.accent;
  }

  Color _getRsiColor(double rsi) {
    if (rsi < 40) return AppTheme.profit;
    if (rsi > 60) return AppTheme.loss;
    return AppTheme.textPrimary;
  }

  Widget _buildCard({required List<Widget> children}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.cardBackground,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: children,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_data == null) {
      return Container(
        color: AppTheme.background,
        child: const Center(child: CircularProgressIndicator(color: AppTheme.accent)),
      );
    }
    
    // UI rendering using 100% guaranteed safe types
    final String status = _data!['status'];
    final String lastUpdate = _data!['lastUpdate'];
    final double btcPrice = _data!['btcPrice'];
    final double btcChange = _data!['btcChange'];
    final double portfolioUsdt = _data!['portfolioUsdt'];
    final double totalPnl = _data!['totalPnl'];
    final double totalPnlPct = _data!['totalPnlPct'];
    final double openPnl = _data!['openPnl'];
    final String regime = _data!['regime'];
    final int signalScore = _data!['signalScore'];
    final double rsi1h = _data!['rsi1h'];
    final double rsi4h = _data!['rsi4h'];
    final double rsi1d = _data!['rsi1d'];

    return Container(
      color: AppTheme.background,
      child: RefreshIndicator(
        color: AppTheme.accent,
        backgroundColor: AppTheme.cardBackground,
        onRefresh: _fetchData,
        child: ListView(
          padding: const EdgeInsets.all(16),
          physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
          children: [
            // MANUAL CONTROLS
            _buildCard(
              children: [
                const Text('QUICK CONTROLS', style: AppTheme.subtitle),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.profit,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                        onPressed: status == 'RUNNING' ? null : () => _sendControlCmd('start'),
                        child: const Text('▶ START', style: TextStyle(fontWeight: FontWeight.bold)),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.loss,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                        onPressed: status == 'STOPPED' ? null : () => _sendControlCmd('stop'),
                        child: const Text('⏹ STOP', style: TextStyle(fontWeight: FontWeight.bold)),
                      ),
                    ),
                  ],
                ),
              ],
            ),

            // BOT STATUS
            _buildCard(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '🤖 BOT STATUS: $status ${status == 'RUNNING' ? '🟢' : '🔴'}',
                      style: AppTheme.title,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  'Last updated: $lastUpdate',
                  style: AppTheme.caption,
                ),
              ],
            ),

            // BTC PRICE
            _buildCard(
              children: [
                const Text('BTC PRICE', style: AppTheme.subtitle),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Text(
                      '\$$btcPrice',
                      style: AppTheme.display1.copyWith(fontSize: 28),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      btcChange >= 0
                          ? '▲ +$btcChange%'
                          : '▼ $btcChange%',
                      style: TextStyle(
                        color: btcChange >= 0 ? AppTheme.profit : AppTheme.loss,
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ],
            ),

            // PORTFOLIO
            _buildCard(
              children: [
                const Text('PORTFOLIO', style: AppTheme.subtitle),
                const SizedBox(height: 8),
                Text(
                  '\$$portfolioUsdt USDT',
                  style: AppTheme.headline,
                ),
                const SizedBox(height: 8),
                Text(
                  'Total PnL: ${totalPnl >= 0 ? '+' : ''}\$$totalPnl ($totalPnlPct%)',
                  style: TextStyle(
                    color: totalPnl >= 0 ? AppTheme.profit : AppTheme.loss,
                    fontSize: 16,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Open PnL: ${openPnl >= 0 ? '+' : ''}\$$openPnl',
                  style: TextStyle(
                    color: openPnl >= 0 ? AppTheme.profit : AppTheme.loss,
                    fontSize: 16,
                  ),
                ),
              ],
            ),

            // MARKET REGIME
            _buildCard(
              children: [
                const Text('MARKET REGIME', style: AppTheme.subtitle),
                const SizedBox(height: 8),
                Text(
                  '[ $regime ${regime.contains('UP') ? '▲' : (regime.contains('DOWN') ? '▼' : '-')} ]',
                  style: TextStyle(
                    color: _getRegimeColor(regime),
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),

            // SIGNAL SCORE
            _buildCard(
              children: [
                const Text('SIGNAL SCORE', style: AppTheme.subtitle),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: LinearProgressIndicator(
                        value: signalScore / 12.0,
                        backgroundColor: AppTheme.background,
                        color: AppTheme.accent,
                        minHeight: 12,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      '$signalScore/12',
                      style: AppTheme.title,
                    ),
                  ],
                ),
              ],
            ),

            // RSI GAUGES
            _buildCard(
              children: [
                const Text('RSI GAUGES', style: AppTheme.subtitle),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _buildRsiItem('1h', rsi1h),
                    _buildRsiItem('4h', rsi4h),
                    _buildRsiItem('1d', rsi1d),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRsiItem(String label, double value) {
    return Column(
      children: [
        Text(label, style: AppTheme.caption),
        const SizedBox(height: 4),
        Text(
          value.toStringAsFixed(1),
          style: TextStyle(
            color: _getRsiColor(value),
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}
