flutter create spill_frontend
cd spill_frontend
lib/main.dart


import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const SpillApp());
}

// ============================================================
// CONFIGURATION
// ============================================================

class Config {
  // Android Emulator:
  static const String baseUrl = "http://10.0.2.2:5000";

  // Windows / Chrome:
  // static const String baseUrl = "http://127.0.0.1:5000";

  // Physical Android phone:
  // static const String baseUrl = "http://192.168.1.10:5000";
}

// ============================================================
// API SERVICE
// ============================================================

class ApiService {
  static final ApiService instance = ApiService._();

  ApiService._();

  String? csrfToken;
  String cookies = "";

  Future<void> _saveCookies(http.Response response) async {
    final setCookie = response.headers["set-cookie"];

    if (setCookie == null) return;

    final cookieParts = setCookie.split(",");

    final List<String> extracted = [];

    for (final part in cookieParts) {
      final first = part.split(";").first.trim();

      if (first.contains("=")) {
        extracted.add(first);
      }
    }

    if (extracted.isNotEmpty) {
      cookies = extracted.join("; ");
    }
  }

  Map<String, String> _headers({
    bool json = true,
    bool csrf = false,
  }) {
    final headers = <String, String>{
      "Accept": "application/json",
    };

    if (json) {
      headers["Content-Type"] = "application/json";
    }

    if (cookies.isNotEmpty) {
      headers["Cookie"] = cookies;
    }

    if (csrf && csrfToken != null) {
      headers["X-CSRF-Token"] = csrfToken!;
    }

    return headers;
  }

  Future<dynamic> get(String path) async {
    final response = await http.get(
      Uri.parse("${Config.baseUrl}$path"),
      headers: _headers(),
    );

    await _saveCookies(response);

    return _decode(response);
  }

  Future<dynamic> post(
    String path, {
    Map<String, dynamic>? body,
    bool csrf = true,
  }) async {
    final response = await http.post(
      Uri.parse("${Config.baseUrl}$path"),
      headers: _headers(csrf: csrf),
      body: body == null ? null : jsonEncode(body),
    );

    await _saveCookies(response);

    return _decode(response);
  }

  Future<dynamic> put(
    String path, {
    Map<String, dynamic>? body,
    bool csrf = true,
  }) async {
    final response = await http.put(
      Uri.parse("${Config.baseUrl}$path"),
      headers: _headers(csrf: csrf),
      body: body == null ? null : jsonEncode(body),
    );

    await _saveCookies(response);

    return _decode(response);
  }

  Future<dynamic> delete(
    String path, {
    bool csrf = true,
  }) async {
    final response = await http.delete(
      Uri.parse("${Config.baseUrl}$path"),
      headers: _headers(csrf: csrf),
    );

    await _saveCookies(response);

    return _decode(response);
  }

  dynamic _decode(http.Response response) {
    dynamic data;

    try {
      data = jsonDecode(response.body);
    } catch (_) {
      data = {
        "success": false,
        "message": "Invalid server response."
      };
    }

    if (response.statusCode >= 400) {
      throw Exception(
        data["message"] ?? "Something went wrong."
      );
    }

    return data;
  }

  Future<void> initialize() async {
    try {
      final result = await get("/api/csrf");

      csrfToken = result["data"]["csrf_token"];
    } catch (_) {}
  }

  Future<Map<String, dynamic>> me() async {
    return await get("/api/auth/me");
  }

  Future<Map<String, dynamic>> login(
    String login,
    String password,
  ) async {
    final result = await post(
      "/api/auth/login",
      body: {
        "login": login,
        "password": password,
      },
    );

    return result;
  }

  Future<Map<String, dynamic>> register(
    String username,
    String email,
    String password,
  ) async {
    final result = await post(
      "/api/auth/register",
      body: {
        "username": username,
        "email": email,
        "password": password,
      },
    );

    return result;
  }

  Future<void> logout() async {
    await post("/api/auth/logout");
    cookies = "";
    csrfToken = null;
  }

  Future<List<dynamic>> getPosts() async {
    final result = await get("/api/posts");

    return result["data"]["posts"] ?? [];
  }

  Future<List<dynamic>> getCategories() async {
    final result = await get("/api/categories");

    return result["data"] ?? [];
  }

  Future<Map<String, dynamic>> createPost(
    String content,
    int? categoryId,
  ) async {
    final result = await post(
      "/api/posts",
      body: {
        "content": content,
        if (categoryId != null) "category_id": categoryId,
      },
    );

    return result["data"];
  }

  Future<void> deletePost(int id) async {
    await delete("/api/posts/$id");
  }

  Future<void> updatePost(
    int id,
    String content,
  ) async {
    await put(
      "/api/posts/$id",
      body: {
        "content": content,
      },
    );
  }

  Future<List<dynamic>> getComments(int postId) async {
    final result = await get(
      "/api/posts/$postId/comments"
    );

    return result["data"] ?? [];
  }

  Future<void> addComment(
    int postId,
    String content,
  ) async {
    await post(
      "/api/posts/$postId/comments",
      body: {
        "content": content,
      },
    );
  }

  Future<void> deleteComment(int id) async {
    await delete(
      "/api/comments/$id"
    );
  }

  Future<Map<String, dynamic>> react(
    int postId,
    String type,
  ) async {
    final result = await post(
      "/api/posts/$postId/react",
      body: {
        "reaction_type": type,
      },
    );

    return result["data"];
  }

  Future<void> savePost(int postId) async {
    await post(
      "/api/posts/$postId/save"
    );
  }

  Future<List<dynamic>> savedPosts() async {
    final result = await get(
      "/api/saved"
    );

    return result["data"] ?? [];
  }

  Future<List<dynamic>> mySpills() async {
    final result = await get(
      "/api/my-spills"
    );

    return result["data"]["posts"] ?? [];
  }

  Future<List<dynamic>> search(
    String query,
  ) async {
    final result = await get(
      "/api/search?q=${Uri.encodeQueryComponent(query)}"
    );

    return result["data"] ?? [];
  }

  Future<List<dynamic>> trending() async {
    final result = await get(
      "/api/trending"
    );

    return result["data"] ?? [];
  }

  Future<Map<String, dynamic>?> teaOfDay() async {
    final result = await get(
      "/api/tea-of-the-day"
    );

    return result["data"];
  }

  Future<void> reportPost(
    int postId,
    String reason,
    String details,
  ) async {
    await post(
      "/api/posts/$postId/report",
      body: {
        "reason": reason,
        "details": details,
      },
    );
  }

  Future<Map<String, dynamic>> profile() async {
    final result = await get(
      "/api/profile"
    );

    return result["data"];
  }

  Future<Map<String, dynamic>> createPoll(
    String question,
    List<String> options,
  ) async {
    final result = await post(
      "/api/polls",
      body: {
        "question": question,
        "options": options,
      },
    );

    return result["data"];
  }

  Future<Map<String, dynamic>> getPoll(
    int pollId,
  ) async {
    final result = await get(
      "/api/polls/$pollId"
    );

    return result["data"];
  }

  Future<void> votePoll(
    int pollId,
    int optionId,
  ) async {
    await post(
      "/api/polls/$pollId/vote",
      body: {
        "option_id": optionId,
      },
    );
  }
}

// ============================================================
// APP
// ============================================================

class SpillApp extends StatelessWidget {
  const SpillApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "SPILL ☕",

      debugShowCheckedModeBanner: false,

      theme: ThemeData(
        useMaterial3: true,

        scaffoldBackgroundColor:
            const Color(0xFFF8F5F1),

        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF7B4B2A),
          brightness: Brightness.light,
        ),

        fontFamily: "Arial",

        appBarTheme: const AppBarTheme(
          backgroundColor:
              Color(0xFFF8F5F1),

          elevation: 0,

          foregroundColor:
              Color(0xFF211A16),
        ),

        inputDecorationTheme:
            InputDecorationTheme(
          filled: true,

          fillColor: Colors.white,

          border: OutlineInputBorder(
            borderRadius:
                BorderRadius.circular(16),

            borderSide: BorderSide.none,
          ),

          enabledBorder:
              OutlineInputBorder(
            borderRadius:
                BorderRadius.circular(16),

            borderSide: BorderSide.none,
          ),

          focusedBorder:
              OutlineInputBorder(
            borderRadius:
                BorderRadius.circular(16),

            borderSide:
                const BorderSide(
              color:
                  Color(0xFF7B4B2A),
            ),
          ),
        ),
      ),

      home: const StartupScreen(),
    );
  }
}

// ============================================================
// STARTUP
// ============================================================

class StartupScreen extends StatefulWidget {
  const StartupScreen({super.key});

  @override
  State<StartupScreen> createState() =>
      _StartupScreenState();
}

class _StartupScreenState
    extends State<StartupScreen> {

  @override
  void initState() {
    super.initState();

    start();
  }

  Future<void> start() async {

    await ApiService.instance.initialize();

    try {

      final result =
          await ApiService.instance.me();

      if (!mounted) return;

      if (result["data"]["authenticated"] == true) {

        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (_) =>
                const MainScreen(),
          ),
        );

      } else {

        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (_) =>
                const LoginScreen(),
          ),
        );
      }

    } catch (_) {

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) =>
              const LoginScreen(),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment:
              MainAxisAlignment.center,

          children: [

            const Text(
              "SPILL ☕",
              style: TextStyle(
                fontSize: 46,
                fontWeight: FontWeight.w900,
              ),
            ),

            const SizedBox(height: 12),

            Text(
              "Your campus. Your stories.",
              style: TextStyle(
                color: Colors.grey.shade600,
                fontSize: 16,
              ),
            ),

            const SizedBox(height: 40),

            const CircularProgressIndicator(),
          ],
        ),
      ),
    );
  }
}

// ============================================================
// LOGIN
// ============================================================

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() =>
      _LoginScreenState();
}

class _LoginScreenState
    extends State<LoginScreen> {

  final loginController =
      TextEditingController();

  final passwordController =
      TextEditingController();

  bool loading = false;

  Future<void> login() async {

    setState(() {
      loading = true;
    });

    try {

      await ApiService.instance.login(
        loginController.text.trim(),
        passwordController.text,
      );

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) =>
              const MainScreen(),
        ),
      );

    } catch (e) {

      showMessage(
        context,
        e.toString().replaceFirst(
          "Exception: ",
          "",
        ),
      );

    } finally {

      if (mounted) {
        setState(() {
          loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(

      body: SafeArea(

        child: Center(

          child: SingleChildScrollView(

            padding:
                const EdgeInsets.all(28),

            child: ConstrainedBox(

              constraints:
                  const BoxConstraints(
                maxWidth: 450,
              ),

              child: Column(

                crossAxisAlignment:
                    CrossAxisAlignment.start,

                children: [

                  const Text(
                    "SPILL ☕",
                    style: TextStyle(
                      fontSize: 46,
                      fontWeight:
                          FontWeight.w900,
                    ),
                  ),

                  const SizedBox(
                    height: 8,
                  ),

                  const Text(
                    "Got something to spill?",
                    style: TextStyle(
                      fontSize: 22,
                      fontWeight:
                          FontWeight.w600,
                    ),
                  ),

                  const SizedBox(
                    height: 8,
                  ),

                  Text(
                    "Your campus. Your stories. "
                    "No names attached.",
                    style: TextStyle(
                      color:
                          Colors.grey.shade600,
                      fontSize: 15,
                    ),
                  ),

                  const SizedBox(
                    height: 35,
                  ),

                  TextField(
                    controller:
                        loginController,

                    decoration:
                        const InputDecoration(
                      labelText:
                          "Username or Email",
                      prefixIcon:
                          Icon(Icons.person),
                    ),
                  ),

                  const SizedBox(
                    height: 16,
                  ),

                  TextField(
                    controller:
                        passwordController,

                    obscureText: true,

                    decoration:
                        const InputDecoration(
                      labelText: "Password",
                      prefixIcon:
                          Icon(Icons.lock),
                    ),
                  ),

                  const SizedBox(
                    height: 24,
                  ),

                  SizedBox(
                    width: double.infinity,

                    height: 54,

                    child: FilledButton(
                      onPressed:
                          loading
                              ? null
                              : login,

                      child: loading
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child:
                                  CircularProgressIndicator(
                                strokeWidth: 2,
                              ),
                            )
                          : const Text(
                              "Log in",
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight:
                                    FontWeight.bold,
                              ),
                            ),
                    ),
                  ),

                  const SizedBox(
                    height: 18,
                  ),

                  Center(
                    child: TextButton(
                      onPressed: () {

                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) =>
                                const RegisterScreen(),
                          ),
                        );
                      },

                      child: const Text(
                        "New to SPILL? Create an account",
                      ),
                    ),
                  ),

                  const SizedBox(
                    height: 25,
                  ),

                  const SafetyBox(),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ============================================================
// REGISTER
// ============================================================

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() =>
      _RegisterScreenState();
}

class _RegisterScreenState
    extends State<RegisterScreen> {

  final username =
      TextEditingController();

  final email =
      TextEditingController();

  final password =
      TextEditingController();

  final confirmPassword =
      TextEditingController();

  bool loading = false;

  Future<void> register() async {

    if (password.text !=
        confirmPassword.text) {

      showMessage(
        context,
        "Passwords do not match.",
      );

      return;
    }

    setState(() {
      loading = true;
    });

    try {

      await ApiService.instance.register(
        username.text.trim(),
        email.text.trim(),
        password.text,
      );

      if (!mounted) return;

      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(
          builder: (_) =>
              const MainScreen(),
        ),
        (route) => false,
      );

    } catch (e) {

      showMessage(
        context,
        e.toString().replaceFirst(
          "Exception: ",
          "",
        ),
      );

    } finally {

      if (mounted) {

        setState(() {
          loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(

      appBar: AppBar(),

      body: SafeArea(

        child: SingleChildScrollView(

          padding:
              const EdgeInsets.all(24),

          child: Center(

            child: ConstrainedBox(

              constraints:
                  const BoxConstraints(
                maxWidth: 500,
              ),

              child: Column(

                crossAxisAlignment:
                    CrossAxisAlignment.start,

                children: [

                  const Text(
                    "Create your SPILL account",
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight:
                          FontWeight.w800,
                    ),
                  ),

                  const SizedBox(
                    height: 8,
                  ),

                  Text(
                    "Your identity stays hidden on "
                    "public spills.",
                    style: TextStyle(
                      color:
                          Colors.grey.shade600,
                    ),
                  ),

                  const SizedBox(
                    height: 30,
                  ),

                  TextField(
                    controller: username,
                    decoration:
                        const InputDecoration(
                      labelText: "Username",
                    ),
                  ),

                  const SizedBox(
                    height: 15,
                  ),

                  TextField(
                    controller: email,
                    keyboardType:
                        TextInputType.emailAddress,
                    decoration:
                        const InputDecoration(
                      labelText: "Email",
                    ),
                  ),

                  const SizedBox(
                    height: 15,
                  ),

                  TextField(
                    controller: password,
                    obscureText: true,
                    decoration:
                        const InputDecoration(
                      labelText: "Password",
                    ),
                  ),

                  const SizedBox(
                    height: 15,
                  ),

                  TextField(
                    controller:
                        confirmPassword,
                    obscureText: true,
                    decoration:
                        const InputDecoration(
                      labelText:
                          "Confirm Password",
                    ),
                  ),

                  const SizedBox(
                    height: 25,
                  ),

                  SizedBox(
                    width: double.infinity,
                    height: 52,

                    child: FilledButton(
                      onPressed:
                          loading
                              ? null
                              : register,

                      child: loading
                          ? const CircularProgressIndicator()
                          : const Text(
                              "Create account",
                            ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ============================================================
// MAIN SCREEN
// ============================================================

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() =>
      _MainScreenState();
}

class _MainScreenState
    extends State<MainScreen> {

  int currentIndex = 0;

  final pages = const [

    HomePage(),

    ExplorePage(),

    CreatePage(),

    SavedPage(),

    ProfilePage(),
  ];

  @override
  Widget build(BuildContext context) {

    return Scaffold(

      body: IndexedStack(
        index: currentIndex,
        children: pages,
      ),

      bottomNavigationBar:
          NavigationBar(

        selectedIndex:
            currentIndex,

        onDestinationSelected:
            (index) {

          setState(() {
            currentIndex = index;
          });
        },

        destinations: const [

          NavigationDestination(
            icon:
                Icon(Icons.home_outlined),
            selectedIcon:
                Icon(Icons.home),
            label: "Home",
          ),

          NavigationDestination(
            icon:
                Icon(Icons.explore_outlined),
            selectedIcon:
                Icon(Icons.explore),
            label: "Explore",
          ),

          NavigationDestination(
            icon:
                Icon(Icons.add_circle_outline),
            selectedIcon:
                Icon(Icons.add_circle),
            label: "Spill",
          ),

          NavigationDestination(
            icon:
                Icon(Icons.bookmark_outline),
            selectedIcon:
                Icon(Icons.bookmark),
            label: "Saved",
          ),

          NavigationDestination(
            icon:
                Icon(Icons.person_outline),
            selectedIcon:
                Icon(Icons.person),
            label: "Profile",
          ),
        ],
      ),
    );
  }
}

// ============================================================
// HOME PAGE
// ============================================================

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() =>
      _HomePageState();
}

class _HomePageState
    extends State<HomePage> {

  bool loading = true;

  List<dynamic> posts = [];

  Map<String, dynamic>? tea;

  @override
  void initState() {
    super.initState();

    load();
  }

  Future<void> load() async {

    setState(() {
      loading = true;
    });

    try {

      final results =
          await Future.wait([

        ApiService.instance.getPosts(),

        ApiService.instance.teaOfDay(),
      ]);

      posts =
          results[0] as List<dynamic>;

      tea =
          results[1] as Map<String, dynamic>?;

    } catch (e) {

      if (mounted) {

        showMessage(
          context,
          e.toString().replaceFirst(
            "Exception: ",
            "",
          ),
        );
      }

    } finally {

      if (mounted) {

        setState(() {
          loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(

      appBar: AppBar(

        title: const Text(
          "SPILL ☕",
          style: TextStyle(
            fontWeight: FontWeight.w900,
          ),
        ),

        actions: [

          IconButton(
            icon:
                const Icon(Icons.refresh),

            onPressed: load,
          ),
        ],
      ),

      body: RefreshIndicator(

        onRefresh: load,

        child: loading

            ? const Center(
                child:
                    CircularProgressIndicator(),
              )

            : posts.isEmpty

                ? ListView(
                    children: const [
                      SizedBox(height: 160),
                      EmptyState(
                        title:
                            "Nothing spilled yet.",
                        subtitle:
                            "Be the first one.",
                      ),
                    ],
                  )

                : ListView(

                    padding:
                        const EdgeInsets.fromLTRB(
                      16,
                      10,
                      16,
                      30,
                    ),

                    children: [

                      if (tea != null)
                        TeaCard(
                          post: tea!,
                        ),

                      const SizedBox(
                        height: 12,
                      ),

                      ...posts.map(
                        (post) =>
                            PostCard(
                          post: post,
                          onChanged: load,
                        ),
                      ),
                    ],
                  ),
      ),
    );
  }
}

// ============================================================
// EXPLORE
// ============================================================

class ExplorePage extends StatefulWidget {
  const ExplorePage({super.key});

  @override
  State<ExplorePage> createState() =>
      _ExplorePageState();
}

class _ExplorePageState
    extends State<ExplorePage> {

  final searchController =
      TextEditingController();

  List<dynamic> results = [];

  bool loading = false;

  Future<void> search() async {

    if (searchController.text.trim().length <
        2) {

      return;
    }

    setState(() {
      loading = true;
    });

    try {

      results =
          await ApiService.instance.search(
        searchController.text.trim(),
      );

    } catch (e) {

      showMessage(
        context,
        e.toString().replaceFirst(
          "Exception: ",
          "",
        ),
      );

    } finally {

      if (mounted) {

        setState(() {
          loading = false;
        });
      }
    }
  }

  Future<void> trending() async {

    setState(() {
      loading = true;
    });

    try {

      results =
          await ApiService.instance.trending();

    } catch (e) {

      showMessage(
        context,
        e.toString().replaceFirst(
          "Exception: ",
          "",
        ),
      );

    } finally {

      if (mounted) {

        setState(() {
          loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(

      appBar: AppBar(
        title: const Text(
          "Explore",
          style: TextStyle(
            fontWeight:
                FontWeight.w800,
          ),
        ),
      ),

      body: ListView(

        padding:
            const EdgeInsets.all(16),

        children: [

          TextField(

            controller:
                searchController,

            onSubmitted: (_) =>
                search(),

            decoration:
                InputDecoration(

              hintText:
                  "Search spills...",

              prefixIcon:
                  const Icon(
                Icons.search,
              ),

              suffixIcon:
                  IconButton(
                onPressed: search,
                icon:
                    const Icon(
                  Icons.arrow_forward,
                ),
              ),
            ),
          ),

          const SizedBox(
            height: 15,
          ),

          Row(
            children: [

              Expanded(
                child: OutlinedButton.icon(
                  onPressed:
                      trending,

                  icon:
                      const Icon(
                    Icons.local_fire_department,
                  ),

                  label:
                      const Text(
                    "Trending",
                  ),
                ),
              ),

              const SizedBox(
                width: 10,
              ),

              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () {

                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) =>
                            const CategoriesPage(),
                      ),
                    );
                  },

                  icon:
                      const Icon(
                    Icons.category_outlined,
                  ),

                  label:
                      const Text(
                    "Categories",
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(
            height: 20,
          ),

          if (loading)
            const Center(
              child:
                  CircularProgressIndicator(),
            ),

          if (!loading &&
              results.isEmpty)
            const EmptyState(
              title:
                  "Explore SPILL",
              subtitle:
                  "Search campus stories or check trending spills.",
            ),

          ...results.map(
            (post) =>
                PostCard(
              post: post,
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================
// CATEGORIES
// ============================================================

class CategoriesPage extends StatefulWidget {
  const CategoriesPage({super.key});

  @override
  State<CategoriesPage> createState() =>
      _CategoriesPageState();
}

class _CategoriesPageState
    extends State<CategoriesPage> {

  List<dynamic> categories = [];

  bool loading = true;

  @override
  void initState() {
    super.initState();

    load();
  }

  Future<void> load() async {

    try {

      categories =
          await ApiService.instance
              .getCategories();

    } catch (e) {

      showMessage(
        context,
        e.toString(),
      );

    } finally {

      if (mounted) {

        setState(() {
          loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(

      appBar: AppBar(
        title:
            const Text("Categories"),
      ),

      body: loading

          ? const Center(
              child:
                  CircularProgressIndicator(),
            )

          : GridView.builder(

              padding:
                  const EdgeInsets.all(16),

              gridDelegate:
                  const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                childAspectRatio: 1.2,
              ),

              itemCount:
                  categories.length,

              itemBuilder:
                  (context, index) {

                final category =
                    categories[index];

                return Card(

                  elevation: 0,

                  child: Padding(

                    padding:
                        const EdgeInsets.all(16),

                    child: Column(

                      mainAxisAlignment:
                          MainAxisAlignment.center,

                      children: [

                        const Icon(
                          Icons.local_cafe,
                          size: 32,
                        ),

                        const SizedBox(
                          height: 10,
                        ),

                        Text(
                          category["name"],
                          textAlign:
                              TextAlign.center,
                          style:
                              const TextStyle(
                            fontWeight:
                                FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),

                        const SizedBox(
                          height: 5,
                        ),

                        Text(
                          category[
                                  "description"] ??
                              "",
                          textAlign:
                              TextAlign.center,
                          maxLines: 2,
                          overflow:
                              TextOverflow.ellipsis,
                          style:
                              TextStyle(
                            fontSize: 12,
                            color:
                                Colors.grey.shade600,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}

// ============================================================
// CREATE PAGE
// ============================================================

class CreatePage extends StatefulWidget {
  const CreatePage({super.key});

  @override
  State<CreatePage> createState() =>
      _CreatePageState();
}

class _CreatePageState
    extends State<CreatePage> {

  final




pubspec.yaml
dependencies:
  flutter:
    sdk: flutter

  cupertino_icons: ^1.0.8
  http: ^1.5.0
flutter pub get