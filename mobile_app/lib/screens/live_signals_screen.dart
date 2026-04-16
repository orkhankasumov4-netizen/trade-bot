import 'dart:convert';
import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../app_theme.dart';

class LiveSignalsScreen extends StatefulWidget {
  const LiveSignalsScreen({Key? key}) : super(key: key);

  @override
  _LiveSignalsScreenState createState() => _LiveSignalsScreenState();
}

class _LiveSignalsScreenState extends State<LiveSignalsScreen> {
  bool _isLoading = true;
  List<dynamic> _signals = [];
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _fetchSignals();
    _refreshTimer = Timer.periodic(const Duration(seconds: 15), (timer) {
      _fetchSignals(isBackground: true);
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchSignals({bool isBackground = false}) async {
    if (!isBackground) setState(() => _isLoading = true);
    
    try {
      final response = await ApiService().get(context, '/signals/live');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _signals = data['signals'] ?? [];
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
      _signals = [
        {
          'time': '14:30',
          'regime': 'TRENDING UP',
          'score': 8,
          'action': 'BUY',
          'reasons': [
            {'text': 'RSI oversold (38.2)', 'passed': true},
            {'text': 'Near Bollinger lower band', 'passed': true},
            {'text': 'Volume spike (1.8x)', 'passed': true},
            {'text': 'No divergence', 'passed': false},
          ]
        },
        {
          'time': '13:45',
          'regime': 'SIDEWAYS',
          'score': 4,
          'action': 'HOLD',
          'reasons': [
            {'text': 'RSI neutral (45.1)', 'passed': false},
            {'text': 'Middle of Bollinger Bands', 'passed': false},
            {'text': 'Low volume', 'passed': false},
          ]
        },
        {
          'time': '12:15',
          'regime': 'TRENDING DOWN',
          'score': 9,
          'action': 'SELL',
          'reasons': [
            {'text': 'RSI overbought (72.5)', 'passed': true},
            {'text': 'MACD bearish cross', 'passed': true},
            {'text': 'Volume spike on red candle', 'passed': true},
          ]
        }
      ];
    });
  }

  Color _getCardColor(String action) {
    if (action == 'BUY') return AppTheme.profit.withOpacity(0.1);
    if (action == 'SELL') return AppTheme.loss.withOpacity(0.1);
    return AppTheme.grey.withOpacity(0.3); // HOLD
  }

  Color _getBorderColor(String action) {
    if (action == 'BUY') return AppTheme.profit;
    if (action == 'SELL') return AppTheme.loss;
    return AppTheme.grey; // HOLD
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.background,
      child: _isLoading && _signals.isEmpty
          ? const Center(child: CircularProgressIndicator(color: AppTheme.accent))
          : RefreshIndicator(
              color: AppTheme.accent,
              backgroundColor: AppTheme.cardBackground,
              onRefresh: () => _fetchSignals(isBackground: false),
              child: ListView.builder(
                padding: const EdgeInsets.all(16),
                physics: const AlwaysScrollableScrollPhysics(),
                itemCount: _signals.length,
                itemBuilder: (context, index) {
                  final signal = _signals[index];
                  final action = signal['action'] ?? 'HOLD';
                  
                  return Container(
                    margin: const EdgeInsets.only(bottom: 16),
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: _getCardColor(action),
                      border: Border.all(color: _getBorderColor(action), width: 1.5),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              '${signal['time']}  ${signal['regime']}',
                              style: const TextStyle(
                                  color: AppTheme.textPrimary,
                                  fontWeight: FontWeight.bold),
                            ),
                            Icon(
                              action == 'BUY' ? Icons.arrow_upward : (action == 'SELL' ? Icons.arrow_downward : Icons.remove),
                              color: _getBorderColor(action),
                            )
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Score: ${signal['score']}/12  → ${(action == 'BUY' ? '★ ' : '')}$action',
                          style: TextStyle(
                            color: _getBorderColor(action),
                            fontSize: 18,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 12),
                        ...((signal['reasons'] as List<dynamic>?) ?? []).map((reason) {
                          bool passed = reason['passed'] ?? false;
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 4),
                            child: Row(
                              children: [
                                Text(
                                  passed ? '✓ ' : '✗ ',
                                  style: TextStyle(color: passed ? AppTheme.profit : AppTheme.loss),
                                ),
                                Text(
                                  reason['text'],
                                  style: const TextStyle(color: AppTheme.textSecondary),
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                      ],
                    ),
                  );
                },
              ),
            ),
    );
  }
}
