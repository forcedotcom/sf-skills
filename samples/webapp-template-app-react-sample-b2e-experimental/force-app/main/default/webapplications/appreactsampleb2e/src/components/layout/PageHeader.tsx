interface PageHeaderProps {
	title: string;
	description?: string;
}

/**
 * Page title and optional description. Uses a consistent wrapper (max-w-7xl mx-auto px-8 pt-8)
 * so the header aligns with list/content on all pages.
 */
export function PageHeader({ title, description }: PageHeaderProps) {
	return (
		<div className="max-w-7xl mx-auto px-8 pt-8">
			<div className="mb-6">
				<h1 className="text-2xl font-bold text-gray-900">{title}</h1>
				{description != null && description !== "" && (
					<p className="text-gray-600 mt-1">{description}</p>
				)}
			</div>
		</div>
	);
}
