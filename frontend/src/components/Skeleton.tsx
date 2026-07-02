export function SkeletonBar({ className = "" }: { className?: string }) {
  return <div className={`animate-skeleton rounded-full bg-slate-700 ${className}`} />;
}

export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-4">
      <SkeletonBar className="mb-2 h-3 w-20" />
      <SkeletonBar className="h-6 w-16" />
    </div>
  );
}

export function SkeletonRow() {
  return (
    <div className="flex items-center gap-3">
      <SkeletonBar className="h-3 w-6" />
      <SkeletonBar className="h-3 w-36" />
      <SkeletonBar className="h-5 flex-1" />
      <SkeletonBar className="h-3 w-12" />
    </div>
  );
}
