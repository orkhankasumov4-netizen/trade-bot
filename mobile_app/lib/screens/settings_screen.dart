import 'dart:convert';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../app_theme.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({Key? key}) : super(key: key);

  @override
  _SettingsScreenState createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  double _stopLossPct = 4.0;
  double _takeProfitPct = 10.0;
  double _maxPositionSizePct = 20.0;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _fetchSettings();
  }

  Future<void> _fetchSettings() async {
    setState(() => _isLoading = true);
    try {
      final response = await ApiService().get(context, '/settings');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _stopLossPct = (data['stopLossPct'] ?? 4.0).toDouble();
          _takeProfitPct = (data['takeProfitPct'] ?? 10.0).toDouble();
          _maxPositionSizePct = (data['maxPositionSizePct'] ?? 20.0).toDouble();
        });
      }
    } catch (e) {
      // Ignore fallback to defaults
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _saveSettings() async {
    final bool? confirm = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          backgroundColor: AppTheme.cardBackground,
          title: const Text('Confirm Changes', style: TextStyle(color: AppTheme.textPrimary)),
          content: const Text(
            '⚠️ This will affect live trading. Continue?',
            style: TextStyle(color: AppTheme.textSecondary),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('CANCEL', style: TextStyle(color: AppTheme.textSecondary)),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('CONTINUE', style: TextStyle(color: AppTheme.accent)),
            ),
          ],
        );
      },
    );

    if (confirm != true) return;

    setState(() => _isLoading = true);
    try {
      final response = await ApiService().put(context, '/settings', {
        'stopLossPct': _stopLossPct,
        'takeProfitPct': _takeProfitPct,
        'maxPositionSizePct': _maxPositionSizePct,
      });

      if (response.statusCode == 200) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Settings saved successfully'),
              backgroundColor: AppTheme.profit,
            ),
          );
        }
      } else {
        throw Exception('Failed to save settings');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Error saving settings'),
            backgroundColor: AppTheme.loss,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Widget _buildSliderSetting({
    required String title,
    required double value,
    required double min,
    required double max,
    required ValueChanged<double> onChanged,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.cardBackground,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(title, style: AppTheme.title),
              Text(
                '${value.toStringAsFixed(1)}%',
                style: const TextStyle(
                  color: AppTheme.accent,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SliderTheme(
            data: SliderTheme.of(context).copyWith(
              activeTrackColor: AppTheme.accent,
              inactiveTrackColor: AppTheme.grey,
              thumbColor: AppTheme.accent,
              overlayColor: AppTheme.accent.withOpacity(0.2),
            ),
            child: Slider(
              value: value,
              min: min,
              max: max,
              divisions: ((max - min) * 10).toInt(),
              onChanged: onChanged,
            ),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('${min.toInt()}%', style: AppTheme.caption),
              Text('${max.toInt()}%', style: AppTheme.caption),
            ],
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.background,
      child: _isLoading && _stopLossPct == 4.0 // Show loader only on initial load if needed
          ? const Center(child: CircularProgressIndicator(color: AppTheme.accent))
          : ListView(
              padding: const EdgeInsets.all(16),
              physics: const BouncingScrollPhysics(),
              children: [
                _buildSliderSetting(
                  title: 'Stop-loss',
                  value: _stopLossPct,
                  min: 1.0,
                  max: 10.0,
                  onChanged: (val) => setState(() => _stopLossPct = val),
                ),
                _buildSliderSetting(
                  title: 'Take-profit',
                  value: _takeProfitPct,
                  min: 5.0,
                  max: 30.0,
                  onChanged: (val) => setState(() => _takeProfitPct = val),
                ),
                _buildSliderSetting(
                  title: 'Max Position Size',
                  value: _maxPositionSizePct,
                  min: 5.0,
                  max: 50.0,
                  onChanged: (val) => setState(() => _maxPositionSizePct = val),
                ),
                const SizedBox(height: 32),
                SizedBox(
                  height: 50,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.accent,
                      foregroundColor: AppTheme.background,
                      textStyle: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    onPressed: _isLoading ? null : _saveSettings,
                    child: _isLoading
                        ? const SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(
                              color: AppTheme.background,
                            ),
                          )
                        : const Text('Save Settings'),
                  ),
                ),
              ],
            ),
    );
  }
}
