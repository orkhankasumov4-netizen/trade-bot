import 'dart:io';
import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../api_config.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  final _storage = const FlutterSecureStorage();
  String? _token;

  Future<void> init() async {
    _token = await _storage.read(key: 'jwt_token');
  }

  Future<void> saveToken(String token) async {
    _token = token;
    await _storage.write(key: 'jwt_token', value: token);
  }

  Future<void> clearToken() async {
    _token = null;
    await _storage.delete(key: 'jwt_token');
  }

  bool get isAuthenticated => _token != null;

  Map<String, String> _getHeaders() {
    return {
      'Content-Type': 'application/json',
      if (_token != null) 'Authorization': 'Bearer $_token',
    };
  }

  void _handleUnauthorized(BuildContext context) {
    clearToken();
    if (context.mounted) {
      Navigator.of(context).pushReplacementNamed('/login');
    }
  }

  Future<http.Response> get(BuildContext context, String endpoint) async {
    try {
      final response = await http.get(
        Uri.parse('$BASE_URL$endpoint'), 
        headers: _getHeaders()
      ).timeout(const Duration(seconds: 10));
      
      if (response.statusCode == 401) {
        _handleUnauthorized(context);
      }
      return response;
    } on SocketException {
      throw Exception('No Internet connection');
    } on TimeoutException {
      throw Exception('API timed out');
    } on FormatException {
      throw Exception('Bad API response format');
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  Future<http.Response> post(BuildContext context, String endpoint, [Map<String, dynamic>? body]) async {
    try {
      final response = await http.post(
        Uri.parse('$BASE_URL$endpoint'),
        headers: _getHeaders(),
        body: body != null ? jsonEncode(body) : null,
      ).timeout(const Duration(seconds: 10));
      
      if (response.statusCode == 401) {
        _handleUnauthorized(context);
      }
      return response;
    } on SocketException {
      throw Exception('No Internet connection');
    } on TimeoutException {
      throw Exception('API timed out');
    } on FormatException {
      throw Exception('Bad API response format');
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  Future<http.Response> put(BuildContext context, String endpoint, [Map<String, dynamic>? body]) async {
    try {
      final response = await http.put(
        Uri.parse('$BASE_URL$endpoint'),
        headers: _getHeaders(),
        body: body != null ? jsonEncode(body) : null,
      ).timeout(const Duration(seconds: 10));
      
      if (response.statusCode == 401) {
        _handleUnauthorized(context);
      }
      return response;
    } on SocketException {
      throw Exception('No Internet connection');
    } on TimeoutException {
      throw Exception('API timed out');
    } on FormatException {
      throw Exception('Bad API response format');
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }
}
