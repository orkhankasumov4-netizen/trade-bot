import 'dart:convert';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../app_theme.dart';
import '../navigation_home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({Key? key}) : super(key: key);

  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _checkLoginStatus();
  }

  Future<void> _checkLoginStatus() async {
    await ApiService().init();
    if (ApiService().isAuthenticated) {
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (context) => NavigationHomeScreen()),
        );
      }
    }
  }

  Future<void> _login() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      final response = await ApiService().post(context, '/auth/login', {
        'username': _usernameController.text,
        'password': _passwordController.text,
      });

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final token = data['access_token'] ?? data['token'];
        
        if (token != null) {
          await ApiService().saveToken(token);
          if (mounted) {
            Navigator.of(context).pushReplacement(
              MaterialPageRoute(builder: (context) => NavigationHomeScreen()),
            );
          }
        } else {
          setState(() {
            _errorMessage = 'Login succeeded but token was missing from response.';
          });
        }
      } else {
        setState(() {
          _errorMessage = 'Invalid credentials or server error.';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceAll('Exception: ', '');
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'BOT LOGIN',
                style: AppTheme.display1.copyWith(color: AppTheme.accent),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 48),
              if (_errorMessage.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 16.0),
                  child: Text(
                    _errorMessage,
                    style: const TextStyle(color: AppTheme.loss),
                    textAlign: TextAlign.center,
                  ),
                ),
              TextField(
                controller: _usernameController,
                style: const TextStyle(color: AppTheme.textPrimary),
                decoration: InputDecoration(
                  labelText: 'Username',
                  labelStyle: const TextStyle(color: AppTheme.textSecondary),
                  enabledBorder: const OutlineInputBorder(
                    borderSide: BorderSide(color: AppTheme.textSecondary),
                  ),
                  focusedBorder: const OutlineInputBorder(
                    borderSide: BorderSide(color: AppTheme.accent),
                  ),
                  filled: true,
                  fillColor: AppTheme.cardBackground,
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _passwordController,
                obscureText: true,
                style: const TextStyle(color: AppTheme.textPrimary),
                decoration: InputDecoration(
                  labelText: 'Password',
                  labelStyle: const TextStyle(color: AppTheme.textSecondary),
                  enabledBorder: const OutlineInputBorder(
                    borderSide: BorderSide(color: AppTheme.textSecondary),
                  ),
                  focusedBorder: const OutlineInputBorder(
                    borderSide: BorderSide(color: AppTheme.accent),
                  ),
                  filled: true,
                  fillColor: AppTheme.cardBackground,
                ),
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
                  onPressed: _isLoading ? null : _login,
                  child: _isLoading
                      ? const SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(
                            color: AppTheme.background,
                          ),
                        )
                      : const Text('Login'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
