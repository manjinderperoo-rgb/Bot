require('dotenv').config();
const makeWASocket = require('@whiskeysockets/baileys').default;
const {
  DisconnectReason,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
} = require('@whiskeysockets/baileys');

const fs = require('fs');
const axios = require('axios'); // Essential for AI API calls
const fsp = require("fs/promises");
const { execFile } = require("child_process");
const pino = require('pino');
const path = require('path');
const qrcode = require('qrcode-terminal');
const { exec } = require('child_process');

// --- Welcome DB ---
const WELCOME_DB_PATH = path.join(__dirname, "welcomed.json");
let welcomedUsers = [];
if (fs.existsSync(WELCOME_DB_PATH)) {
  try { welcomedUsers = JSON.parse(fs.readFileSync(WELCOME_DB_PATH)); } catch { welcomedUsers = []; }
}
function saveWelcomed() {
  fs.writeFileSync(WELCOME_DB_PATH, JSON.stringify(welcomedUsers, null, 2));
}

// --- Bot start time for uptime ---
const botStartTime = Date.now();
function formatUptime(ms) {
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${h}h ${m}m ${s % 60}s`;
}
// --- GLOBAL VARIABLES FOR AI MODE ---
const usersInAiMode = new Set(); // Stores JIDs of users currently in AI mode
const userConversationHistory = new Map(); // Stores conversation history for each user

const users = new Set(); // For initial welcome message, keeping it.

// Helper function to execute shell commands
function executeCommand(command) {
  return new Promise((resolve, reject) => {
    exec(command, (error, stdout, stderr) => {
      if (error) {
        console.error(`exec error: ${error.message}`);
        return reject(error);
      }
      if (stderr) {
        console.warn(`exec stderr: ${stderr}`);
      }
      resolve(stdout);
    });
  });
}

async function startBot() {
  const { state, saveCreds } = await useMultiFileAuthState('sessions');
  const { version } = await fetchLatestBaileysVersion();

  const sock = makeWASocket({
    version,
    auth: state,
    logger: pino({ level: 'silent' }), // Suppress Baileys logs for cleaner output
  });

  // Save credentials when updated
  sock.ev.on('creds.update', saveCreds);

  // Handle connection updates (QR code, disconnection, reconnection)
  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      // Display QR code for linking WhatsApp
      qrcode.generate(qr, { small: true });
      console.log('Scan the QR code above to connect your WhatsApp!');
    }

    if (connection === 'close') {
      const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
      console.log('🔁 Connection closed, trying to reconnect...', lastDisconnect?.error);
      // Reconnect unless explicitly logged out
      if (shouldReconnect) {
        startBot();
      } else {
        console.log('❌ Connection logged out. Please delete the sessions folder and restart the bot.');
      }
    } else if (connection === 'open') {
      console.log('✅ Bot is now connected!');
    }
  });

  // Handle incoming messages
  sock.ev.on('messages.upsert', async ({ messages }) => {
    const msg = messages[0];
    // Ignore messages from self or if no message content
    if (!msg.message || msg.key.fromMe) return;

    const from = msg.key.remoteJid;
    const text = msg.message.conversation || msg.message.extendedTextMessage?.text || "";

    // Send welcome message to new users
    // Persistent welcome: only first time ever
if (!welcomedUsers.includes(from)) {
  welcomedUsers.push(from);
  saveWelcomed();
  await sock.sendMessage(from, {
    text: "👋 *Welcome to Faizan's Bot!*\nType `start` to get started."
  });
  return;
}

    const isCommand = text.trim().toLowerCase();

    // --- AI MODE COMMANDS ---

    // Command to enter AI conversational mode
    if (isCommand === 'enteraimode') {
        if (usersInAiMode.has(from)) {
            await sock.sendMessage(from, { text: "💡 You are already in AI mode." });
        } else {
            usersInAiMode.add(from);
            // Initialize history for new AI mode user
            userConversationHistory.set(from, []);
            await sock.sendMessage(from, { text: "🚀 *AI Mode Activated!* You can now chat directly with me. I'll remember our conversation.\n\nType `exitaimode` to leave." });
        }
        return;
    }

    // Command to exit AI conversational mode
    if (isCommand === 'exitaimode') {
        if (usersInAiMode.has(from)) {
            usersInAiMode.delete(from);
            userConversationHistory.delete(from); // Clear history on exit for privacy/memory
            await sock.sendMessage(from, { text: "👋 *AI Mode Deactivated!* Your previous messages will not be remembered." });
        } else {
            await sock.sendMessage(from, { text: "🤷‍♂️ You are not currently in AI mode." });
        }
        return;
    }

    // --- AI QUESTION ANSWERING LOGIC ---
let isAiQuery = false;
let queryText = '';

// Check if user is in AI mode AND message is not a standard command
if (usersInAiMode.has(from) && !text.startsWith('!')) {
    isAiQuery = true;
    queryText = text.trim();
}

if (isAiQuery) {
    if (!queryText) {
        await sock.sendMessage(from, { text: "❓ Please provide your question." });
        return;
    }

    // Show generating response message
    await sock.sendMessage(from, { text: '🤖 Generating response ⌛...' });

    try {
        const groqApiKey = process.env.GROQ_API_KEY;
        if (!groqApiKey) {
            await sock.sendMessage(from, { text: "❌ API key missing. Ask the bot owner to set GROQ_API_KEY." });
            console.error("GROQ_API_KEY not set");
            return;
        }

        const groqApiBase = "https://api.groq.com/openai/v1";

        // --- Prepare messages with system role ---
        let messages = [];

        if (userConversationHistory.has(from)) {
            messages = userConversationHistory.get(from).slice(); // clone array
        }

        // Ensure system role is always first
        if (!messages.length || messages[0].role !== 'system') {
            messages.unshift({
                role: 'system',
                content: `You are Faizan's helpful bot named Faizan-Bot. Respond helpfully and conversationally.`
            });
        }

        // Add current user query
        messages.push({ role: 'user', content: queryText });

        // Limit history size (keep system role intact)
        const MAX_HISTORY_MESSAGES = 10; // max user+assistant pairs
        if (messages.length > MAX_HISTORY_MESSAGES + 1) { // +1 for system
            const systemMsg = messages.shift(); // remove system
            messages = messages.slice(messages.length - MAX_HISTORY_MESSAGES); // slice last messages
            messages.unshift(systemMsg); // re-add system at first
        }

        // --- API call ---
        const response = await axios.post(
            `${groqApiBase}/chat/completions`,
            {
                model: "meta-llama/llama-4-maverick-17b-128e-instruct",
                messages: messages,
            },
            {
                headers: {
                    'Authorization': `Bearer ${groqApiKey}`,
                    'Content-Type': 'application/json',
                },
            }
        );

        const answer = response.data.choices[0].message.content;

        await sock.sendMessage(from, { text: `🤖 *Answer:*\n\n${answer}` });

        // Update conversation history
        if (usersInAiMode.has(from)) {
            messages.push({ role: "assistant", content: answer });
            userConversationHistory.set(from, messages);
        }

    } catch (error) {
        console.error("❌ AI Error:", error.message);

        // Remove last user message to prevent broken history
        if (usersInAiMode.has(from)) {
            const currentHistory = userConversationHistory.get(from);
            if (currentHistory && currentHistory.length > 0 && currentHistory[currentHistory.length - 1].role === 'user') {
                currentHistory.pop();
                userConversationHistory.set(from, currentHistory);
            }
        }

        // Friendly error message
        let errorMessage = "❌ Failed to answer. Please try again.";
        if (error.response) {
            const status = error.response.status;
            if (status === 404) errorMessage = "❌ AI model not found. Contact the bot owner.";
            else if (status === 401) errorMessage = "❌ Invalid AI API key. Contact the bot owner.";
            else if (status === 400 && error.response.data?.error?.message?.includes('credits')) {
                errorMessage = "❌ AI credits low. Contact the bot owner.";
            } else errorMessage = `❌ Server error ${status}. Please try later.`;
        }
        await sock.sendMessage(from, { text: errorMessage });
    }
    return; // Stop further processing
}

    // --- REGULAR COMMANDS ---

    // QR Command: Sends a QR image if available
    if (['qr'].includes(isCommand)) {
      const qrPath = path.join(__dirname, 'qr.jpg');
      if (fs.existsSync(qrPath)) {
        await sock.sendMessage(from, {
          image: fs.readFileSync(qrPath),
          caption: "📸 Here's your QR Code.\nScan to pay."
        });
      } else {
        await sock.sendMessage(from, { text: "❌ QR image not found on server." });
      }
      return;
    }

    // Start Command: Greets the user and lists basic commands
    if (isCommand === 'start') {
      await sock.sendMessage(from, {
        text: `📲 *Welcome!*
Use the following:
- \`help\` — Show commands
- \`info\` — Your WhatsApp details
- Just paste *Instagram* links to download reel.`
      });
      return;
    }

    // Help Command: Shows all available commands, including AI mode ones
    if (isCommand === 'help') {
      await sock.sendMessage(from, {
        text: `🤖 *Available Commands:*
• *start* — Start the bot
• *help* — Show this help message
• *info* — Display your WhatsApp details
• *qr* — Send my payment QR code
• *botinfo* — Show information about bot
• *enteraimode* — Activate AI conversational mode (bot will remember previous chat)
• *exitaimode* — Deactivate AI conversational mode
• Just paste any *Instagram* link to download reel.`
      });
      return;
    }

    // Info Command: Displays user's WhatsApp details
    if (isCommand === 'info') {
      const pfp = await sock.profilePictureUrl(from, "image").catch(() => null);
      const name = msg.pushName || "Not Available";
      
      await sock.sendMessage(from, {
        text: `📋 *Your Info:*\n• Name: ${name}\n• Number: ${from.split("@")[0]}\n• Device: Unknown\n• Battery: Not Available (Not Available)`
      });

      if (pfp) {
        await sock.sendMessage(from, {
          image: { url: pfp },
          caption: "🖼️ Your profile picture"
        });
      }
      return;
    }

if (isCommand === "botinfo") {
  const uptime = formatUptime(Date.now() - botStartTime);
  await sock.sendMessage(from, {
    image: fs.readFileSync(path.join(__dirname, "owner.jpg")), // local image
    caption:
      `🤖 *Faizan-Bot*\n\n` +
      `Version: 1.2.0 final\n\n` +
      `Owner Name: Jameel Ahemad\n\n` +
      `Owner Social: https://www.instagram.com/__faizan__bolte__07?igsh=MWI2Nm9waTUzeXU1bg==\n\n` +
      `Uptime: ${uptime}`,
    linkPreview: false // Prevent WhatsApp from showing preview
  });
  return;
}
    // Auto Link Detection for Instagram only using yt-dlp
    if (text.includes("instagram.com/")) {
  try {
    globalThis.activeDownloads = globalThis.activeDownloads || {};
    if (globalThis.activeDownloads[msg.key.id]) return;
    globalThis.activeDownloads[msg.key.id] = true;

    await sock.sendMessage(from, { text: "📥 Downloading your Instagram media, please wait..." });

    const outputDir = path.join(__dirname, "downloads");
    await fsp.mkdir(outputDir, { recursive: true });

    const filePrefix = path.join(outputDir, `${msg.key.id}`);
    const ytDlpCommand =
      process.platform === "win32"
        ? path.join(__dirname, "yt-dlp.exe")
        : path.join(__dirname, "yt-dlp");

    // Already downloaded check
    const existing = (await fsp.readdir(outputDir)).filter(f => f.startsWith(msg.key.id));
    if (existing.length) {
      const filePath = path.join(outputDir, existing[0]);
      await sock.sendMessage(from, { video: { url: filePath }, caption: "✅ Already downloaded!" });
      delete globalThis.activeDownloads[msg.key.id];
      return;
    }

    // Get metadata JSON for caption
    let caption = "Instagram Reel";
    try {
      const meta = await new Promise(res =>
        execFile(
          ytDlpCommand,
          ["--dump-single-json", "--no-playlist", text],
          { cwd: __dirname, timeout: 30000 },
          (err, out) => {
            if (err) return res(null);
            try { res(JSON.parse(out)); } catch { res(null); }
          }
        )
      );
      if (meta) {
        const t = meta.title || "Instagram Reel";
        const u = meta.uploader || "";
        const d = meta.description ? `\n\n📝 ${meta.description}` : "";
        caption = `🎬 ${t}${u ? `\n👤 By ${u}` : ""}${d}`;
      }
    } catch {}

    // Download media
    const args = [
      "--cookies", "cookies.txt",
      "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
      "--output", `${filePrefix}.%(ext)s`,
      "--no-playlist",
      text
    ];
    await new Promise((resolve, reject) => {
      execFile(ytDlpCommand, args, { cwd: __dirname, timeout: 180000 }, async (err) => {
        if (err) {
          await sock.sendMessage(from, { text: `❌ Failed: ${err.message}` });
          delete globalThis.activeDownloads[msg.key.id];
          return reject(err);
        }
        const files = (await fsp.readdir(outputDir)).filter(f => f.startsWith(msg.key.id));
        if (files.length) {
          const filePath = path.join(outputDir, files[0]);
          await sock.sendMessage(from, { video: { url: filePath }, caption });
          await fsp.unlink(filePath).catch(()=>{});
        } else {
          await sock.sendMessage(from, { text: "❌ Downloaded but file not found." });
        }
        delete globalThis.activeDownloads[msg.key.id];
        resolve();
      });
    });
  } catch (e) {
    await sock.sendMessage(from, { text: `❌ Error: ${e.message}` });
    delete globalThis.activeDownloads[msg.key.id];
  }
  return;
}

    // If not in AI mode, not a recognized command, and not an Instagram link, then ignore.
    if (!isCommand.match(/^(start|help|info|qr|enteraimode|exitaimode)$/) && !text.includes("instagram.com/") && !usersInAiMode.has(from)) {
      return; 
    }
  });
}

// Start the bot
startBot();

const http = require("http");

const server = http.createServer((req, res) => {
  res.writeHead(200, { "Content-Type": "text/plain" });
  res.end("Bot is alive");
});

const PORT = process.env.PORT || 10000;

server.listen(PORT, () => {
  console.log(`🌐 Keep-alive server running on port ${PORT}`);
});

startBot();