
import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const SearchTriageApp());
}

class SearchTriageApp extends StatelessWidget {
  const SearchTriageApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Search Term Triage',
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF245B91),
        ),
      ),
      home: const DashboardPage(),
    );
  }
}

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  // Chrome on the same computer:
  static const String apiUrl =
      'http://127.0.0.1:8000/triage/upload';

  // For Android emulator, replace the URL above with:
  // http://10.0.2.2:8000/triage/upload

  bool loading = false;
  String statusMessage = 'Upload your Google Ads CSV to get started.';
  Map<String, dynamic>? report;
  String filter = 'all';

  Future<void> uploadFile() async {
    final selection = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['csv'],
    );

    if (selection == null || selection.files.isEmpty) return;

    final file = selection.files.first;

    if (file.bytes == null && file.path == null) {
      setState(() => statusMessage = 'Could not access this file.');
      return;
    }

    setState(() {
      loading = true;
      report = null;
      statusMessage = 'Analyzing your search terms...';
    });

    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse(apiUrl),
      );

      if (file.bytes != null) {
        request.files.add(
          http.MultipartFile.fromBytes(
            'file',
            file.bytes!,
            filename: file.name,
          ),
        );
      } else {
        request.files.add(
          await http.MultipartFile.fromPath(
            'file',
            file.path!,
          ),
        );
      }

      final streamed = await request.send().timeout(
        const Duration(seconds: 60),
      );

      final response = await http.Response.fromStream(streamed);
      final body = jsonDecode(response.body);

      if (response.statusCode != 200) {
        throw Exception(
          body is Map
              ? body['detail'] ?? 'Upload failed'
              : 'Upload failed',
        );
      }

      setState(() {
        report = Map<String, dynamic>.from(body);
        statusMessage = 'Analysis completed successfully.';
        filter = 'all';
      });
    } catch (e) {
      setState(() {
        statusMessage = 'Could not analyze the file: $e';
      });
    } finally {
      if (mounted) {
        setState(() => loading = false);
      }
    }
  }

  Color decisionColor(String decision) {
    switch (decision) {
      case 'promote':
        return const Color(0xFF16804A);
      case 'block':
        return const Color(0xFFD63838);
      default:
        return const Color(0xFFB77908);
    }
  }

  Widget metricCard(
      String title,
      dynamic value,
      IconData icon,
      Color color,
      ) {
    return Container(
      width: 155,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withAlpha(18),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withAlpha(70)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 25),
          const SizedBox(height: 12),
          Text(
            '$value',
            style: TextStyle(
              fontSize: 27,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          Text(title, style: const TextStyle(fontSize: 13)),
        ],
      ),
    );
  }

  Widget buildResultCard(Map<String, dynamic> row) {
    final decision = row['decision'] as String;
    final color = decisionColor(decision);
    final confidence =
    ((row['confidence'] as num) * 100).round();
    final needsReview = row['review_required'] == true;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey.withAlpha(65)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${row['query']}',
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: [
              Chip(
                label: Text(decision.toUpperCase()),
                backgroundColor: color.withAlpha(25),
                side: BorderSide(color: color),
              ),
              Chip(label: Text('$confidence% confidence')),
            ],
          ),
          Text(
            '${row['reason']}',
            style: const TextStyle(height: 1.4),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 6,
            children: [
              Text('Clicks: ${row['clicks']}'),
              Text('Cost: ${row['cost']}'),
              Text('Conversions: ${row['conversions']}'),
            ],
          ),
          if (needsReview) ...[
            const SizedBox(height: 12),
            const Row(
              children: [
                Icon(
                  Icons.rate_review_outlined,
                  color: Colors.deepOrange,
                ),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Human review required',
                    style: TextStyle(
                      color: Colors.deepOrange,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final rows = (report?['results'] as List<dynamic>? ?? [])
        .map((item) => Map<String, dynamic>.from(item))
        .where((item) =>
    filter == 'all' || item['decision'] == filter)
        .toList();

    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF173F68),
        foregroundColor: Colors.white,
        title: const Text(
          'Search Term Triage',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        actions: const [
          Padding(
            padding: EdgeInsets.only(right: 16),
            child: Icon(Icons.analytics_outlined),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [
                  Color(0xFF173F68),
                  Color(0xFF327BB7),
                ],
              ),
              borderRadius: BorderRadius.circular(20),
            ),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.query_stats,
                  color: Colors.white,
                  size: 40,
                ),
                SizedBox(height: 15),
                Text(
                  'Make smarter search decisions.',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 10),
                Text(
                  'Analyze search terms, understand '
                      'recommendations and identify cases '
                      'that need human review.',
                  style: TextStyle(
                    color: Colors.white,
                    height: 1.5,
                  ),
                ),
                SizedBox(height: 12),
                Text(
                  'PS-01 • Explainable classification',
                  style: TextStyle(
                    color: Colors.white70,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          SizedBox(
            height: 54,
            child: FilledButton.icon(
              onPressed: loading ? null : uploadFile,
              icon: const Icon(Icons.upload_file),
              label: const Text('Upload Search-Term CSV'),
            ),
          ),
          const SizedBox(height: 12),
          if (loading)
            const LinearProgressIndicator(),
          const SizedBox(height: 8),
          Text(
            statusMessage,
            style: TextStyle(
              color: report == null
                  ? Theme.of(context).colorScheme.onSurface
                  : Colors.green,
            ),
          ),
          if (report != null) ...[
            const SizedBox(height: 22),
            const Text(
              'Analysis Overview',
              style: TextStyle(
                fontSize: 21,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                metricCard(
                  'Total Terms',
                  report!['total_terms'],
                  Icons.search,
                  Colors.blue,
                ),
                metricCard(
                  'Promote',
                  report!['promote'],
                  Icons.trending_up,
                  Colors.green,
                ),
                metricCard(
                  'Block',
                  report!['block'],
                  Icons.block,
                  Colors.red,
                ),
                metricCard(
                  'Ignore',
                  report!['ignore'],
                  Icons.remove_circle_outline,
                  Colors.orange,
                ),
                metricCard(
                  'Needs Review',
                  report!['review_required'],
                  Icons.rate_review_outlined,
                  Colors.deepOrange,
                ),
              ],
            ),
            const SizedBox(height: 24),
            const Text(
              'Search Term Decisions',
              style: TextStyle(
                fontSize: 21,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: filter,
              decoration: const InputDecoration(
                labelText: 'Filter decisions',
                border: OutlineInputBorder(),
              ),
              items: const [
                DropdownMenuItem(
                  value: 'all',
                  child: Text('All decisions'),
                ),
                DropdownMenuItem(
                  value: 'promote',
                  child: Text('Promote'),
                ),
                DropdownMenuItem(
                  value: 'block',
                  child: Text('Block'),
                ),
                DropdownMenuItem(
                  value: 'ignore',
                  child: Text('Ignore'),
                ),
              ],
              onChanged: (value) {
                if (value != null) {
                  setState(() => filter = value);
                }
              },
            ),
            const SizedBox(height: 14),
            if (rows.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text('No terms match this filter.'),
                ),
              ),
            ...rows.map(buildResultCard),
          ],
          const SizedBox(height: 25),
          const Center(
            child: Text(
              'PS-01 Hackathon Prototype',
              style: TextStyle(color: Colors.grey),
            ),
          ),
        ],
      ),
    );
  }
}
