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
				<div key={i} className="flex items-center rounded-lg bg-gray-50 p-4">
					<Skeleton className="h-12 w-12 shrink-0 rounded-lg" />
					<div className="ml-4 min-w-0 grow space-y-1">
						<div className="flex items-center gap-2">
							<Skeleton className="h-5 w-24" />
							<Skeleton className="h-4 w-20" />
						</div>
						<Skeleton className="h-5 w-3/5" />
					</div>
					<Skeleton className="ml-4 h-7 w-24 shrink-0 rounded-full" />
				</div>
			))}
		</>
	);
}
