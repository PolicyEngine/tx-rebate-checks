'use client';

export default function PolicyOverview() {
  return (
    <div className="space-y-10">
      {/* Summary */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          The proposed Texas $1,500 rebate checks
        </h2>
        <p className="text-gray-700 mb-4">
          As part of her &ldquo;Money in Your Pocket&rdquo; economic
          agenda, Gina Hinojosa — the Democratic nominee for Texas
          governor — proposes that the Legislature deliver $1,500 refund
          checks to Texas families, funded by drawing down the state&apos;s
          ~$27 billion Economic Stabilization Fund while leaving $10
          billion in reserve. This dashboard reports household,
          statewide, and congressional district impacts of the proposal
          for tax year 2027, the first year the next governor could
          deliver it.
        </p>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
          <h3 className="font-semibold text-gray-800 mb-2">The proposal</h3>
          <p className="text-sm text-gray-600">
            A one-time <strong>$1,500 rebate check</strong>{' '}
            for every Texas household &mdash;{' '}
            <strong>one check per household with no income limit</strong>{' '}
            &mdash; paid from the Economic Stabilization Fund (the
            &ldquo;rainy day fund&rdquo;). Drawing the fund from $27
            billion down to a $10 billion reserve frees ~$17 billion,
            covering a check for each of Texas&apos;s ~11&ndash;12 million
            households. Cost estimates are on the Statewide impact tab.
          </p>
        </div>
      </div>

      {/* References */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">References</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-800 mb-2">
              Proposal source
            </h4>
            <ul className="text-sm text-gray-700 space-y-1">
              <li>
                <a
                  href="https://ginafortexas.com/2026/07/recap-gina-hinojosa-launches-money-in-your-pocket-economic-agenda-across-houston-san-antonio-and-laredo/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:underline"
                >
                  Hinojosa campaign press release, &ldquo;RECAP: Gina
                  Hinojosa Launches &lsquo;Money in Your Pocket&rsquo;
                  Economic Agenda&rdquo; (July 13, 2026)
                </a>
              </li>
            </ul>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-800 mb-2">
              Economic Stabilization Fund
            </h4>
            <ul className="text-sm text-gray-700 space-y-1">
              <li>
                <a
                  href="https://comptroller.texas.gov/transparency/revenue/esf/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:underline"
                >
                  Texas Comptroller &mdash; Economic Stabilization Fund
                </a>
              </li>
              <li>
                <a
                  href="https://statutes.capitol.texas.gov/Docs/CN/htm/CN.3.htm#3.49-g"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:underline"
                >
                  Tex. Const. art. III, § 49-g
                </a>
              </li>
            </ul>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-800 mb-2">Calculations</h4>
            <p className="text-sm text-gray-700">
              Powered by{' '}
              <a
                href="https://github.com/PolicyEngine/policyengine-us"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:underline"
              >
                policyengine-us
              </a>
              . PolicyEngine is a nonpartisan nonprofit and does not
              endorse candidates or proposals.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
