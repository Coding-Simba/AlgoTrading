namespace AlgoTrading.Governance
{
    public sealed class SignoffRow
    {
        public string Id { get; }
        public string Title { get; }
        public string SignerRole { get; }
        public string RequiredFor { get; }
        public bool Signed { get; }
        public string SignedBy { get; }
        public string SignedAtIso { get; }
        public string Notes { get; }

        public SignoffRow(string id, string title, string signerRole, string requiredFor,
                          bool signed, string signedBy, string signedAtIso, string notes = "")
        {
            Id = id;
            Title = title;
            SignerRole = signerRole;
            RequiredFor = requiredFor;
            Signed = signed;
            SignedBy = signedBy ?? "";
            SignedAtIso = signedAtIso ?? "";
            Notes = notes ?? "";
        }
    }
}
