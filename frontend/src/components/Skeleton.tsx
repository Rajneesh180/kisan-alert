export default function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="mt-3 space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="skeleton h-4 rounded"
          style={{ width: `${90 - i * 12}%` }}
        />
      ))}
    </div>
  );
}
