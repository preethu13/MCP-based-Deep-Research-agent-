export function Footer() {
  return (
    <footer className="w-full bg-surface-container-lowest mt-space-xl border-t border-surface-container-high/30">
      <div className="max-w-7xl mx-auto px-margin-mobile lg:px-margin py-space-lg flex flex-col md:flex-row items-center justify-between gap-space-md">
        <div className="flex items-center gap-space-sm">
          <span className="w-2 h-2 rounded-full bg-primary"></span>
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Stitch Research Desk · Private & local research analyst ($0 per query)
          </span>
        </div>
        <div className="flex items-center gap-space-lg text-outline font-body-sm text-body-sm">
          <span>Powered by LangGraph & Model Context Protocol</span>
        </div>
      </div>
    </footer>
  );
}
