export default function Demo() {
  return (
    <section id="demo" className="py-20 sm:py-28 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
            See your partner data come to life
          </h2>
          <p className="text-xl text-gray-600">
            Executive dashboards, deal drilldowns, and partner analytics - all in one place.
          </p>
        </div>

        {/* Product Screenshot/Mockup */}
        <div className="relative">
          {/* Browser Chrome */}
          <div className="bg-white rounded-xl shadow-2xl overflow-hidden border border-gray-200">
            {/* Browser Header */}
            <div className="bg-gray-100 px-4 py-3 flex items-center border-b border-gray-200">
              <div className="flex space-x-2">
                <div className="w-3 h-3 rounded-full bg-red-400"></div>
                <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                <div className="w-3 h-3 rounded-full bg-green-400"></div>
              </div>
              <div className="flex-1 flex justify-center">
                <div className="bg-white rounded-md px-4 py-1 text-sm text-gray-500 w-96 text-center">
                  attribution-mvp.yourcompany.com
                </div>
              </div>
            </div>

            {/* App Interface Mockup */}
            <div className="p-6 bg-gray-50">
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-primary-600 rounded-lg"></div>
                  <span className="font-semibold text-gray-900">Attribution MVP</span>
                </div>
                <div className="flex space-x-2">
                  {['Dashboard', 'Partners', 'Deals', 'Rules', 'Reports'].map((tab) => (
                    <div
                      key={tab}
                      className={`px-3 py-1.5 rounded-md text-sm ${
                        tab === 'Dashboard'
                          ? 'bg-primary-600 text-white'
                          : 'text-gray-600 bg-white'
                      }`}
                    >
                      {tab}
                    </div>
                  ))}
                </div>
              </div>

              {/* Dashboard Content */}
              <div className="grid grid-cols-4 gap-4 mb-6">
                {[
                  { label: 'Total Revenue', value: '$2.4M', change: '+12%' },
                  { label: 'Partner Influenced', value: '$1.8M', change: '+24%' },
                  { label: 'Active Partners', value: '47', change: '+5' },
                  { label: 'Open Deals', value: '156', change: '+18' },
                ].map((metric) => (
                  <div key={metric.label} className="bg-white rounded-lg p-4 border border-gray-200">
                    <div className="text-sm text-gray-500 mb-1">{metric.label}</div>
                    <div className="flex items-end justify-between">
                      <span className="text-2xl font-bold text-gray-900">{metric.value}</span>
                      <span className="text-sm text-green-600">{metric.change}</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Charts Row */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                {/* Revenue Chart */}
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <div className="text-sm font-medium text-gray-900 mb-4">Attribution by Partner Type</div>
                  <div className="flex items-end space-x-3 h-32">
                    {[
                      { height: '80%', label: 'SI', color: 'bg-primary-600' },
                      { height: '60%', label: 'Referral', color: 'bg-primary-400' },
                      { height: '45%', label: 'ISV', color: 'bg-primary-300' },
                      { height: '30%', label: 'Influence', color: 'bg-primary-200' },
                    ].map((bar) => (
                      <div key={bar.label} className="flex-1 flex flex-col items-center">
                        <div
                          className={`w-full ${bar.color} rounded-t`}
                          style={{ height: bar.height }}
                        ></div>
                        <span className="text-xs text-gray-500 mt-2">{bar.label}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Pipeline Chart */}
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <div className="text-sm font-medium text-gray-900 mb-4">Deal Pipeline by Stage</div>
                  <div className="space-y-3">
                    {[
                      { stage: 'Discovery', value: 45, width: '90%' },
                      { stage: 'Evaluation', value: 32, width: '64%' },
                      { stage: 'Commit', value: 18, width: '36%' },
                      { stage: 'Live', value: 12, width: '24%' },
                    ].map((item) => (
                      <div key={item.stage} className="flex items-center">
                        <span className="text-xs text-gray-500 w-20">{item.stage}</span>
                        <div className="flex-1 bg-gray-100 rounded-full h-2 mr-3">
                          <div
                            className="bg-primary-600 h-2 rounded-full"
                            style={{ width: item.width }}
                          ></div>
                        </div>
                        <span className="text-xs font-medium text-gray-900 w-8">{item.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Recent Activity */}
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <div className="text-sm font-medium text-gray-900 mb-4">Recent Attribution Events</div>
                <div className="space-y-3">
                  {[
                    { account: 'Acme Corp', partner: 'TechPartners Inc', split: '35%', amount: '$42,000' },
                    { account: 'GlobalTech', partner: 'Solutions Group', split: '25%', amount: '$28,500' },
                    { account: 'DataFlow LLC', partner: 'Cloud Integrators', split: '40%', amount: '$56,000' },
                  ].map((event, i) => (
                    <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                      <div>
                        <span className="text-sm font-medium text-gray-900">{event.account}</span>
                        <span className="text-gray-400 mx-2">→</span>
                        <span className="text-sm text-gray-600">{event.partner}</span>
                      </div>
                      <div className="flex items-center space-x-4">
                        <span className="text-sm text-primary-600 font-medium">{event.split}</span>
                        <span className="text-sm font-semibold text-gray-900">{event.amount}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Floating decorative elements */}
          <div className="absolute -top-4 -right-4 w-24 h-24 bg-primary-100 rounded-full blur-3xl opacity-60"></div>
          <div className="absolute -bottom-4 -left-4 w-32 h-32 bg-primary-200 rounded-full blur-3xl opacity-40"></div>
        </div>

        {/* Feature highlights below screenshot */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-16">
          {[
            {
              title: '12 Integrated Views',
              description: 'Executive dashboard, partner management, deal drilldown, approval queue, and more.',
            },
            {
              title: 'Real-time Updates',
              description: 'Attribution calculations update instantly as deals progress through your pipeline.',
            },
            {
              title: 'Complete Audit Trail',
              description: 'Every attribution decision is logged with full history for compliance and analysis.',
            },
          ].map((item, i) => (
            <div key={i} className="text-center">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{item.title}</h3>
              <p className="text-gray-600">{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
