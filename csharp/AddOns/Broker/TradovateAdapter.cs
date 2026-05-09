using System;
using System.Collections.Generic;
using AlgoTrading.Governance;

namespace AlgoTrading.Broker
{
    /// <summary>
    /// Tradovate broker adapter — refusing stub.
    /// Tradovate (a NinjaTrader Group platform) is the order-routing API used
    /// by NinjaTrader Brokerage. This adapter is the seam we will fill in
    /// once Appendix F is signed. Until then every method raises
    /// BlockedLiveTrading. See docs/broker/ninjatrader_integration.md.
    /// </summary>
    public sealed class TradovateAdapter : LiveBrokerAdapter
    {
        public static readonly string[] RequiredEnvVars =
        {
            "TRADOVATE_CLIENT_ID",
            "TRADOVATE_CLIENT_SECRET",
            "TRADOVATE_USERNAME",
            "TRADOVATE_PASSWORD",
            "TRADOVATE_APP_NAME",
            "TRADOVATE_ENV"
        };

        public const string DemoBaseUrl = "https://demo.tradovateapi.com/v1";
        public const string LiveBaseUrl = "https://live.tradovateapi.com/v1";

        public string Env { get; }
        private readonly Dictionary<string, string> _credentials;

        public TradovateAdapter(SignoffMatrix matrix, string env, Dictionary<string, string> credentials)
            : base(matrix)
        {
            if (env != "demo" && env != "live")
                throw new BlockedLiveTrading(
                    "BLOCKED_LIVE_TRADING: TRADOVATE_ENV must be 'demo' or 'live', got '" + env + "'");
            Env = env;
            _credentials = credentials ?? new Dictionary<string, string>();
        }

        public string BaseUrl => Env == "live" ? LiveBaseUrl : DemoBaseUrl;

        public static TradovateAdapter FromEnvironment(SignoffMatrix matrix)
        {
            var missing = new List<string>();
            var creds = new Dictionary<string, string>();
            foreach (var v in RequiredEnvVars)
            {
                var value = Environment.GetEnvironmentVariable(v);
                if (string.IsNullOrEmpty(value)) missing.Add(v);
                else creds[v] = value;
            }
            if (missing.Count > 0)
                throw new BlockedLiveTrading(
                    "BLOCKED_LIVE_TRADING: missing Tradovate environment variables: " +
                    string.Join(", ", missing) +
                    ". See docs/broker/ninjatrader_integration.md.");
            return new TradovateAdapter(matrix, creds["TRADOVATE_ENV"], creds);
        }

        public override string Submit(BrokerOrder order)
        {
            Gate();
            throw new BlockedLiveTrading(
                "BLOCKED_LIVE_TRADING: Tradovate Submit() is not implemented; " +
                "Appendix F sign-off and the operator runbook in " +
                "docs/broker/ninjatrader_integration.md are prerequisites.");
        }

        public override bool Cancel(string orderId)
        {
            Gate();
            throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: Tradovate Cancel() is not implemented");
        }

        public override int CancelAll()
        {
            Gate();
            throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: Tradovate CancelAll() is not implemented");
        }

        public override IDictionary<string, int> Positions()
        {
            Gate();
            throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: Tradovate Positions() is not implemented");
        }

        public override IList<BrokerOrder> WorkingOrders()
        {
            Gate();
            throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: Tradovate WorkingOrders() is not implemented");
        }

        public override IList<BrokerFill> Fills()
        {
            Gate();
            throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: Tradovate Fills() is not implemented");
        }

        // Implementation seams (deliberately not yet implemented). When
        // Appendix F is signed and this stub is replaced with real code,
        // the public methods above should call into these.

        private string TradovateAuthenticate()
            => throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: TradovateAuthenticate() is a seam stub");

        private string TradovatePlaceOso(BrokerOrder order)
            => throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: TradovatePlaceOso() is a seam stub");

        private bool TradovateCancel(string orderId)
            => throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: TradovateCancel() is a seam stub");

        private void TradovateReconcile()
            => throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: TradovateReconcile() is a seam stub");
    }
}
