import { Skeleton } from "@/components/ui/skeleton";

export function SkeletonField({
	labelWidth = "w-20",
	height = "h-9",
}: {
	labelWidth?: string;
	height?: string;
}) {
	return (
		<div className="space-y-2">
			<Skeleton className={`h-3 ${labelWidth}`} />
			<Skeleton className={`${height} w-full`} />
		</div>
	);
}

export function SkeletonListRows({ count = 3 }: { count?: number }) {
	return (
		<>
			{Array.from({ length: count }, (_, i) => (
				<div key={i} className="flex items-center gap-4 rounded-lg bg-gray-50 p-4">
					<Skeleton className="size-10 shrink-0 rounded-full" />
					<div className="min-w-0 flex-1 space-y-2">
						<Skeleton className="h-4 w-3/4" />
						<Skeleton className="h-3 w-1/2" />
					</div>
					<Skeleton className="h-6 w-16 shrink-0 rounded-full" />
				</div>
			))}
		</>
	);
}
