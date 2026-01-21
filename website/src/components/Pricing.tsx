const tiers = [
  {
    name: 'Starter',
    price: '$299',
    period: '/month',
    description: 'For small teams getting started with partner attribution.',
    features: [
      'Up to 100 accounts',
      'Up to 25 partners',
      '5 attribution rules',
      'CSV exports',
      'Email support',
      'Basic dashboards',
    ],
    cta: 'Start Free Trial',
    highlighted: false,
  },
  {
    name: 'Professional',
    price: '$799',
    period: '/month',
    description: 'For growing teams with complex partner ecosystems.',
    features: [
      'Unlimited accounts',
      'Unlimited partners',
      'Unlimited rules',
      'CSV, Excel & PDF exports',
      'Salesforce integration',
      'AI-powered insights',
      'Priority support',
      'Custom dashboards',
    ],
    cta: 'Start Free Trial',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'For large organizations with advanced requirements.',
    features: [
      'Everything in Professional',
      'PostgreSQL deployment',
      'SSO/SAML authentication',
      'Custom integrations',
      'Dedicated success manager',
      'SLA guarantees',
      'On-premise option',
      'Advanced security',
    ],
    cta: 'Contact Sales',
    highlighted: false,
  },
]

export default function Pricing() {
  return (
    <section id="pricing" className="py-20 sm:py-28 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
            Simple, transparent pricing
          </h2>
          <p className="text-xl text-gray-600">
            Start with a 14-day free trial. No credit card required.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {tiers.map((tier) => (
            <div
              key={tier.name}
              className={`rounded-2xl p-8 ${
                tier.highlighted
                  ? 'bg-primary-600 text-white ring-4 ring-primary-600 ring-offset-2 scale-105'
                  : 'bg-white border-2 border-gray-100'
              }`}
            >
              <h3
                className={`text-xl font-semibold mb-2 ${
                  tier.highlighted ? 'text-white' : 'text-gray-900'
                }`}
              >
                {tier.name}
              </h3>
              <p
                className={`text-sm mb-6 ${
                  tier.highlighted ? 'text-primary-100' : 'text-gray-500'
                }`}
              >
                {tier.description}
              </p>
              <div className="mb-6">
                <span
                  className={`text-4xl font-bold ${
                    tier.highlighted ? 'text-white' : 'text-gray-900'
                  }`}
                >
                  {tier.price}
                </span>
                <span
                  className={tier.highlighted ? 'text-primary-100' : 'text-gray-500'}
                >
                  {tier.period}
                </span>
              </div>
              <ul className="space-y-3 mb-8">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start">
                    <svg
                      className={`w-5 h-5 mr-3 flex-shrink-0 ${
                        tier.highlighted ? 'text-primary-200' : 'text-primary-600'
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    <span
                      className={`text-sm ${
                        tier.highlighted ? 'text-primary-50' : 'text-gray-600'
                      }`}
                    >
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>
              <a
                href="#contact"
                className={`block text-center py-3 px-6 rounded-lg font-semibold transition-colors ${
                  tier.highlighted
                    ? 'bg-white text-primary-600 hover:bg-primary-50'
                    : 'bg-primary-600 text-white hover:bg-primary-700'
                }`}
              >
                {tier.cta}
              </a>
            </div>
          ))}
        </div>

        {/* FAQ or additional info */}
        <div className="mt-16 text-center">
          <p className="text-gray-600">
            All plans include free setup assistance and data migration support.
          </p>
          <p className="text-gray-500 mt-2 text-sm">
            Need a custom solution?{' '}
            <a href="#contact" className="text-primary-600 hover:underline">
              Let&apos;s talk
            </a>
          </p>
        </div>
      </div>
    </section>
  )
}
