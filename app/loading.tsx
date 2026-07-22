export default function Loading() {
  return (
    <div className="h-[100dvh] flex flex-col overflow-hidden">
      {/* Header 骨架 */}
      <header className="flex items-center justify-between px-4 py-3 bg-white border-b border-bamboo">
        <div className="flex items-center gap-2.5 animate-pulse">
          <div className="w-8 h-8 rounded-md bg-bamboo" />
          <div className="h-5 w-32 rounded bg-bamboo" />
        </div>
        <div className="flex gap-2 animate-pulse">
          <div className="w-10 h-10 rounded-md border border-bamboo" />
          <div className="w-10 h-10 rounded-md border border-bamboo" />
        </div>
      </header>

      {/* Main 骨架 */}
      <main className="flex-1 flex overflow-hidden">
        <div className="flex-1 relative bg-silk flex items-center justify-center">
          {/* 中心加载圈 */}
          <div className="flex flex-col items-center gap-4">
            <div className="relative w-12 h-12">
              <div className="absolute inset-0 rounded-full border-2 border-bamboo" />
              <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-cinnabar animate-spin" />
            </div>
            <div className="font-serif text-sm text-ink-500">正在唤醒历史长河...</div>
          </div>
        </div>
        {/* Sidebar 骨架 */}
        <div className="hidden md:block w-[340px] bg-white border-l border-bamboo">
          <div className="p-4 flex flex-col gap-4 animate-pulse">
            <div className="h-4 w-24 rounded bg-bamboo" />
            <div className="flex flex-wrap gap-1.5">
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="h-6 w-12 rounded-full bg-bamboo" />
              ))}
            </div>
            <div className="h-20 rounded-lg bg-bamboo" />
            <div className="h-4 w-20 rounded bg-bamboo" />
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-12 rounded-md border border-bamboo" />
            ))}
          </div>
        </div>
      </main>

      {/* Timeline 骨架 */}
      <div className="bg-white border-t border-bamboo h-[80px] flex items-center px-4 animate-pulse">
        <div className="w-full h-10 rounded-lg bg-bamboo" />
      </div>
    </div>
  );
}
