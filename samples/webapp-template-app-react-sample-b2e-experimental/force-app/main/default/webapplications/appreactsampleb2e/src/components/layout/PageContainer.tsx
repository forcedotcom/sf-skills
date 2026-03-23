import type { ReactNode } from "react";

interface PageContainerProps {
	children: ReactNode;
}

export function PageContainer({ children }: PageContainerProps) {
	return <div className="min-h-screen bg-gray-50 p-4 md:p-8">{children}</div>;
}
