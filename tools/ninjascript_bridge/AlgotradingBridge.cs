// AlgotradingBridge — NinjaScript AddOn for localhost-only TCP/JSON bridge.
//
// REFUSING-BY-DEFAULT STUB. This file ships compilable but every order
// path raises NotImplementedException. The seams listed in the
// "TODO(NT8 SDK)" comments below need to be filled against the actual
// NinjaTrader 8 SDK on the operator's Windows VM. They are intentionally
// not pre-filled because the live SDK shape (Account / Order / Cbi /
// OrderType) is best verified from the local NinjaTrader install before
// touching real orders.
//
// Deployment:
//   1. Copy this file to:
//        Documents\NinjaTrader 8\bin\Custom\AddOns\AlgotradingBridge.cs
//   2. In NT8: Tools → Edit NinjaScript → AddOn → compile.
//   3. Restart NT8.
//   4. Configure listen host (loopback only), port, and bearer token in
//      the AddOn's settings UI (the OnStateChange seam below holds the
//      placeholder for the configuration dialog).
//
// Wire protocol: see docs/broker/ninjatrader_integration.md.
//
// Security model:
//   - Bind only to 127.0.0.1 / IPv6 ::1. Refuse all other addresses.
//   - First message of every connection MUST be `auth`; reject all
//     other ops on an unauthenticated socket.
//   - Constant-time token comparison.
//   - One concurrent client at a time.

#region Using
using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using NinjaTrader.NinjaScript;
// TODO(NT8 SDK): uncomment as you wire the seams.
// using NinjaTrader.Cbi;
// using NinjaTrader.Core;
#endregion

namespace NinjaTrader.NinjaScript.AddOns
{
    public class AlgotradingBridge : AddOnBase
    {
        // ----- Configuration (set via the AddOn's settings UI; see TODO below).
        private string listenHost = "127.0.0.1";
        private int listenPort = 0;          // operator-supplied; 0 = disabled.
        private string bearerToken = "";     // operator-supplied; 32+ random bytes.
        private string defaultAccount = "";  // operator-supplied; e.g. "Sim101".

        private TcpListener listener;
        private Thread acceptThread;
        private volatile bool running;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Algotrading bridge — refusing-by-default localhost TCP/JSON.";
                Name = "AlgotradingBridge";
            }
            else if (State == State.Configure)
            {
                // TODO(NT8 SDK): replace with values from the AddOn's
                // configuration dialog (NinjaScript exposes a property
                // grid via `[Display(...)]` attributes on serialized
                // members). Until that is wired the AddOn refuses to
                // bind because listenPort defaults to 0.
            }
            else if (State == State.Active)
            {
                if (listenPort == 0)
                {
                    Print("[AlgotradingBridge] disabled: listen port not configured.");
                    return;
                }
                if (!IsLoopback(listenHost))
                {
                    Print("[AlgotradingBridge] refusing to bind to non-loopback host: " + listenHost);
                    return;
                }
                Start();
            }
            else if (State == State.Terminated)
            {
                Stop();
            }
        }

        // ----- Listener lifecycle ------------------------------------

        private void Start()
        {
            try
            {
                listener = new TcpListener(IPAddress.Parse(listenHost), listenPort);
                listener.Start();
                running = true;
                acceptThread = new Thread(AcceptLoop) { IsBackground = true, Name = "AlgotradingBridge.Accept" };
                acceptThread.Start();
                Print("[AlgotradingBridge] listening on " + listenHost + ":" + listenPort);
            }
            catch (Exception ex)
            {
                Print("[AlgotradingBridge] start failed: " + ex.Message);
            }
        }

        private void Stop()
        {
            running = false;
            try { if (listener != null) listener.Stop(); } catch { /* swallow */ }
            try { if (acceptThread != null) acceptThread.Join(TimeSpan.FromSeconds(1)); } catch { /* swallow */ }
        }

        private void AcceptLoop()
        {
            while (running)
            {
                TcpClient client = null;
                try
                {
                    client = listener.AcceptTcpClient();
                }
                catch (SocketException) { return; }
                catch (ObjectDisposedException) { return; }

                if (client == null) continue;

                try { HandleClient(client); }
                catch (Exception ex) { Print("[AlgotradingBridge] client error: " + ex.Message); }
                finally { try { client.Close(); } catch { /* swallow */ } }
            }
        }

        // ----- Per-connection protocol -------------------------------

        private void HandleClient(TcpClient client)
        {
            using (var stream = client.GetStream())
            using (var reader = new StreamReader(stream, Encoding.UTF8))
            using (var writer = new StreamWriter(stream, new UTF8Encoding(false)) { AutoFlush = true, NewLine = "\n" })
            {
                bool authed = false;
                string line;
                while (running && (line = reader.ReadLine()) != null)
                {
                    string op = ParseOp(line);
                    if (op == null)
                    {
                        writer.WriteLine("{\"error\":\"bad_json\"}");
                        return;
                    }

                    if (!authed)
                    {
                        if (op != "auth")
                        {
                            writer.WriteLine("{\"error\":\"unauthenticated\"}");
                            return;
                        }
                        string supplied = ParseField(line, "token");
                        if (supplied == null || !ConstantTimeEquals(supplied, bearerToken))
                        {
                            writer.WriteLine("{\"error\":\"auth_failed\"}");
                            return;
                        }
                        authed = true;
                        writer.WriteLine("{\"ok\":true}");
                        continue;
                    }

                    // Authed — dispatch.
                    switch (op)
                    {
                        case "ping":
                            writer.WriteLine("{\"pong\":" + DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() + "}");
                            break;
                        case "place_bracket":
                            writer.WriteLine(NotImplemented("place_bracket"));
                            break;
                        case "cancel":
                            writer.WriteLine(NotImplemented("cancel"));
                            break;
                        case "cancel_all":
                            writer.WriteLine(NotImplemented("cancel_all"));
                            break;
                        case "positions":
                            writer.WriteLine(NotImplemented("positions"));
                            break;
                        case "working":
                            writer.WriteLine(NotImplemented("working"));
                            break;
                        case "flatten_protected":
                            writer.WriteLine(NotImplemented("flatten_protected"));
                            break;
                        default:
                            writer.WriteLine("{\"error\":\"unknown_op\",\"op\":\"" + Escape(op) + "\"}");
                            break;
                    }
                }
            }
        }

        // ----- Implementation seams (TODO when Appendix F is signed) -----

        // TODO(NT8 SDK): place a bracket order using NT's unmanaged
        // approach. Pseudocode:
        //   var account = Account.All.First(a => a.Name == defaultAccount);
        //   var entry = new OrderEntry { ... };
        //   string ocoId = Guid.NewGuid().ToString();
        //   account.Submit(entry, stopLoss with ocoId, takeProfit with ocoId);
        //   return entry.OrderId;
        private string PlaceBracketSeam(string clientOrderId, string symbol, string side,
                                         int qty, string entryType, decimal entryPrice,
                                         decimal stopLoss, decimal takeProfit)
        {
            throw new NotImplementedException("PlaceBracketSeam");
        }

        // TODO(NT8 SDK): cancel a working order by id.
        private bool CancelSeam(string orderId) { throw new NotImplementedException("CancelSeam"); }

        // TODO(NT8 SDK): cancel every working order in the default account.
        private int CancelAllSeam() { throw new NotImplementedException("CancelAllSeam"); }

        // TODO(NT8 SDK): read position quantities for the default account.
        private string PositionsJsonSeam() { throw new NotImplementedException("PositionsJsonSeam"); }

        // TODO(NT8 SDK): protected flatten — cancel all + market-close
        // any open position. Must NOT short-circuit on cancel failure;
        // attempt the close even if cancel times out.
        private void FlattenProtectedSeam() { throw new NotImplementedException("FlattenProtectedSeam"); }

        // ----- Helpers ----------------------------------------------

        private static string NotImplemented(string op)
        {
            return "{\"error\":\"not_implemented\",\"op\":\"" + Escape(op) + "\"}";
        }

        private static bool IsLoopback(string host)
        {
            return host == "127.0.0.1" || host == "localhost" || host == "::1";
        }

        private static bool ConstantTimeEquals(string a, string b)
        {
            if (a == null || b == null) return false;
            if (a.Length != b.Length) return false;
            int diff = 0;
            for (int i = 0; i < a.Length; i++) diff |= a[i] ^ b[i];
            return diff == 0;
        }

        private static string ParseOp(string line)
        {
            return ParseField(line, "op");
        }

        // Tiny JSON field reader. Sufficient for the flat protocol;
        // replace with a real JSON parser (System.Text.Json or
        // Newtonsoft.Json — NT8 ships neither by default in older
        // installs) when wiring the seams.
        private static string ParseField(string json, string field)
        {
            if (string.IsNullOrEmpty(json) || string.IsNullOrEmpty(field)) return null;
            string needle = "\"" + field + "\"";
            int k = json.IndexOf(needle, StringComparison.Ordinal);
            if (k < 0) return null;
            int colon = json.IndexOf(':', k + needle.Length);
            if (colon < 0) return null;
            int start = colon + 1;
            while (start < json.Length && (json[start] == ' ' || json[start] == '\t')) start++;
            if (start >= json.Length) return null;
            if (json[start] == '"')
            {
                int end = json.IndexOf('"', start + 1);
                if (end < 0) return null;
                return json.Substring(start + 1, end - start - 1);
            }
            int term = start;
            while (term < json.Length && json[term] != ',' && json[term] != '}') term++;
            return json.Substring(start, term - start).Trim();
        }

        private static string Escape(string s)
        {
            if (s == null) return "";
            var sb = new StringBuilder(s.Length);
            foreach (char c in s)
            {
                if (c == '"') sb.Append("\\\"");
                else if (c == '\\') sb.Append("\\\\");
                else if (c < 0x20) sb.Append(" ");
                else sb.Append(c);
            }
            return sb.ToString();
        }

        // Suppress unused-warning for the seams until they are wired.
        private void _silence_unused_warnings()
        {
            _ = PlaceBracketSeam("", "", "", 0, "", 0, 0, 0);
            _ = CancelSeam("");
            _ = CancelAllSeam();
            _ = PositionsJsonSeam();
            FlattenProtectedSeam();
            _ = SHA256.Create();
        }
    }
}
