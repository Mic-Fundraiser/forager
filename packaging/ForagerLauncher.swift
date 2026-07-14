// Forager — guscio nativo macOS (WKWebView) attorno al server Flask locale.
// Avvia il server Python in background e mostra l'app in una finestra nativa,
// senza browser. Compilato in Contents/MacOS/Forager da build_macapp.py.
import Cocoa
import WebKit

let FORAGER_PORT: UInt16 = 7421

func portOpen(_ port: UInt16) -> Bool {
    let fd = socket(AF_INET, SOCK_STREAM, 0)
    if fd < 0 { return false }
    defer { close(fd) }
    var addr = sockaddr_in()
    addr.sin_family = sa_family_t(AF_INET)
    addr.sin_port = port.bigEndian
    addr.sin_addr.s_addr = inet_addr("127.0.0.1")
    let r = withUnsafePointer(to: &addr) { ptr in
        ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) { sa in
            connect(fd, sa, socklen_t(MemoryLayout<sockaddr_in>.size))
        }
    }
    return r == 0
}

func loadingHTML() -> String {
    return """
    <!doctype html><html><head><meta charset='utf-8'><style>
    html,body{height:100%;margin:0}
    body{background:#0e0e12;color:#f4f4f6;display:flex;align-items:center;justify-content:center;
         font-family:-apple-system,Inter,sans-serif;flex-direction:column;gap:22px}
    .ring{width:46px;height:46px;border:3px solid #2a2a30;border-top-color:#ffd100;border-radius:50%;
          animation:s .8s linear infinite}
    @keyframes s{to{transform:rotate(360deg)}}
    .t{font-size:14px;color:#8a8a92;letter-spacing:.02em}
    b{color:#fff;font-weight:600}
    </style></head><body>
    <div class='ring'></div><div class='t'>Avvio di <b>Forager</b>…</div>
    </body></html>
    """
}

class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate {
    var window: NSWindow!
    var webView: WKWebView!
    var server: Process?

    func applicationDidFinishLaunching(_ note: Notification) {
        buildMenu()

        let res = Bundle.main.resourcePath ?? "."
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        let data = home + "/Library/Application Support/Forager"
        let fm = FileManager.default
        try? fm.createDirectory(atPath: data + "/data", withIntermediateDirectories: true)
        try? fm.createDirectory(atPath: data + "/backups", withIntermediateDirectories: true)

        let rect = NSRect(x: 0, y: 0, width: 1280, height: 820)
        window = NSWindow(contentRect: rect,
                          styleMask: [.titled, .closable, .miniaturizable, .resizable],
                          backing: .buffered, defer: false)
        window.title = "Forager"
        window.minSize = NSSize(width: 980, height: 640)
        window.setFrameAutosaveName("ForagerMainWindow")

        let config = WKWebViewConfiguration()
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")
        webView = WKWebView(frame: rect, configuration: config)
        webView.autoresizingMask = [.width, .height]
        webView.navigationDelegate = self
        window.contentView = webView
        if window.frame.width < 100 { window.setFrame(rect, display: false) }
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        webView.loadHTMLString(loadingHTML(), baseURL: nil)

        if !portOpen(FORAGER_PORT) {
            startServer(res: res, data: data, home: home)
        }
        waitForServerThenLoad()
    }

    func startServer(res: String, data: String, home: String) {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: res + "/python/bin/python3")
        p.arguments = [res + "/app/app.py"]
        p.currentDirectoryURL = URL(fileURLWithPath: res + "/app")

        var env = ProcessInfo.processInfo.environment
        env["FORAGER_DATA_DIR"] = data
        env["FORAGER_HOST"] = "127.0.0.1"
        env["FORAGER_PORT"] = String(FORAGER_PORT)
        env["PYTHONPYCACHEPREFIX"] = data + "/pycache"
        let dyld = [res + "/libs", "/opt/homebrew/lib", "/usr/local/lib"].joined(separator: ":")
        env["DYLD_FALLBACK_LIBRARY_PATH"] = dyld + ":" + (env["DYLD_FALLBACK_LIBRARY_PATH"] ?? "")
        env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin:" + home + "/.local/bin"
        p.environment = env

        let logPath = data + "/forager.log"
        if !FileManager.default.fileExists(atPath: logPath) {
            FileManager.default.createFile(atPath: logPath, contents: nil)
        }
        if let lh = FileHandle(forWritingAtPath: logPath) {
            lh.seekToEndOfFile()
            p.standardOutput = lh
            p.standardError = lh
        }
        do { try p.run(); server = p } catch { NSLog("Forager: server non avviato: \(error)") }
    }

    func waitForServerThenLoad() {
        DispatchQueue.global().async {
            for _ in 0..<160 {
                if portOpen(FORAGER_PORT) {
                    DispatchQueue.main.async {
                        let url = URL(string: "http://127.0.0.1:\(FORAGER_PORT)/")!
                        self.webView.load(URLRequest(url: url))
                    }
                    return
                }
                usleep(250_000)
            }
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ s: NSApplication) -> Bool { true }

    func applicationWillTerminate(_ note: Notification) {
        server?.terminate()
    }

    // Link esterni (LinkedIn, email, docs…) → browser/Mail di sistema, non nella finestra app.
    func webView(_ wv: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if let url = action.request.url {
            let host = url.host ?? ""
            let scheme = url.scheme ?? ""
            let isLocal = host == "127.0.0.1" || host == "localhost" || host.isEmpty
            if !isLocal && (scheme == "http" || scheme == "https" || scheme == "mailto" || scheme == "tel") {
                NSWorkspace.shared.open(url)
                decisionHandler(.cancel)
                return
            }
        }
        decisionHandler(.allow)
    }

    @objc func reloadWeb() { webView.reload() }

    @objc func showAbout() {
        let credits = NSMutableAttributedString()
        let attr: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 11),
            .foregroundColor: NSColor.labelColor,
            .paragraphStyle: { let p = NSMutableParagraphStyle(); p.alignment = .center; p.lineSpacing = 2; return p }(),
        ]
        func text(_ s: String) { credits.append(NSAttributedString(string: s, attributes: attr)) }
        func link(_ s: String, _ url: String) {
            var a = attr
            a[.link] = url
            a[.foregroundColor] = NSColor.linkColor
            credits.append(NSAttributedString(string: s, attributes: a))
        }
        text("CRM open-source per fundraiser\n\n")
        text("Creato da Michelangelo Gigli\n")
        link("info@michelangelogigli.it", "mailto:info@michelangelogigli.it")
        text("\n")
        link("linkedin.com/in/gigli-michelangelo", "https://www.linkedin.com/in/gigli-michelangelo/")
        text("\n\nOpen Source")
        let opts: [NSApplication.AboutPanelOptionKey: Any] = [
            .credits: credits,
            NSApplication.AboutPanelOptionKey(rawValue: "Copyright"): "© 2026 Michelangelo Gigli · Open Source",
        ]
        NSApp.orderFrontStandardAboutPanel(options: opts)
    }

    func buildMenu() {
        let main = NSMenu()

        let appItem = NSMenuItem()
        main.addItem(appItem)
        let appMenu = NSMenu()
        let about = NSMenuItem(title: "Informazioni su Forager", action: #selector(showAbout), keyEquivalent: "")
        about.target = self
        appMenu.addItem(about)
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Nascondi Forager", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(withTitle: "Esci da Forager", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu

        let editItem = NSMenuItem()
        main.addItem(editItem)
        let editMenu = NSMenu(title: "Modifica")
        editMenu.addItem(withTitle: "Annulla", action: Selector(("undo:")), keyEquivalent: "z")
        editMenu.addItem(withTitle: "Ripeti", action: Selector(("redo:")), keyEquivalent: "Z")
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(withTitle: "Taglia", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "Copia", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "Incolla", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: "Seleziona tutto", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editItem.submenu = editMenu

        let viewItem = NSMenuItem()
        main.addItem(viewItem)
        let viewMenu = NSMenu(title: "Vista")
        let reload = NSMenuItem(title: "Ricarica", action: #selector(reloadWeb), keyEquivalent: "r")
        reload.target = self
        viewMenu.addItem(reload)
        viewItem.submenu = viewMenu

        let winItem = NSMenuItem()
        main.addItem(winItem)
        let winMenu = NSMenu(title: "Finestra")
        winMenu.addItem(withTitle: "Minimizza", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        winMenu.addItem(withTitle: "Ingrandisci", action: #selector(NSWindow.performZoom(_:)), keyEquivalent: "")
        winItem.submenu = winMenu
        NSApp.windowsMenu = winMenu

        NSApp.mainMenu = main
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.regular)
let delegate = AppDelegate()
app.delegate = delegate
app.run()
