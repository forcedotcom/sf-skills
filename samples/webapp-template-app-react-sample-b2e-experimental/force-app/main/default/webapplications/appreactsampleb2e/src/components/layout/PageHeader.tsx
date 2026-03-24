interface PageHeaderProps {
	title: string;
	description: string;
}

/**
 * Page title and optional description. Uses a consistent wrapper (max-w-7xl mx-auto px-8 pt-8)
 * so the header aligns with list/content on all pages.
 */
export function PageHeader({ title, description }: PageHeaderProps) {
	return (
		<div>
			<h1 className="text-2xl font-bold text-gray-900">{title}</h1>
			{description !== "" && <p className="text-gray-800 mt-1">{description}</p>}
		</div>
	);
}
