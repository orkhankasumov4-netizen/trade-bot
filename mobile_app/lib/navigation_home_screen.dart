import 'package:best_flutter_ui_templates/app_theme.dart';
import 'package:best_flutter_ui_templates/custom_drawer/drawer_user_controller.dart';
import 'package:best_flutter_ui_templates/custom_drawer/home_drawer.dart';
import 'package:best_flutter_ui_templates/screens/dashboard_screen.dart';
import 'package:best_flutter_ui_templates/screens/trade_history_screen.dart';
import 'package:best_flutter_ui_templates/screens/live_signals_screen.dart';
import 'package:best_flutter_ui_templates/screens/settings_screen.dart';
import 'package:best_flutter_ui_templates/screens/bot_control_screen.dart';
import 'package:flutter/material.dart';

class NavigationHomeScreen extends StatefulWidget {
  @override
  _NavigationHomeScreenState createState() => _NavigationHomeScreenState();
}

class _NavigationHomeScreenState extends State<NavigationHomeScreen> {
  Widget? screenView;
  DrawerIndex? drawerIndex;

  @override
  void initState() {
    drawerIndex = DrawerIndex.DASHBOARD;
    screenView = const DashboardScreen();
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.background,
      child: SafeArea(
        top: false,
        bottom: false,
        child: Scaffold(
          backgroundColor: AppTheme.background,
          body: DrawerUserController(
            screenIndex: drawerIndex,
            drawerWidth: MediaQuery.of(context).size.width * 0.75,
            onDrawerCall: (DrawerIndex drawerIndexdata) {
              changeIndex(drawerIndexdata);
              //callback from drawer for replace screen as user need with passing DrawerIndex(Enum index)
            },
            screenView: screenView,
            //we replace screen view as we need on navigate starting screens like MyHomePage, HelpScreen, FeedbackScreen, etc...
          ),
        ),
      ),
    );
  }

  void changeIndex(DrawerIndex drawerIndexdata) {
    if (drawerIndex != drawerIndexdata) {
      drawerIndex = drawerIndexdata;
      switch (drawerIndex) {
        case DrawerIndex.DASHBOARD:
          setState(() {
            screenView = const DashboardScreen();
          });
          break;
        case DrawerIndex.TRADES:
          setState(() {
            screenView = const TradeHistoryScreen();
          });
          break;
        case DrawerIndex.SIGNALS:
          setState(() {
            screenView = const LiveSignalsScreen();
          });
          break;
        case DrawerIndex.SETTINGS:
          setState(() {
            screenView = const SettingsScreen();
          });
          break;
        case DrawerIndex.CONTROL:
          setState(() {
            screenView = const BotControlScreen();
          });
          break;
        default:
          break;
      }
    }
  }
}
