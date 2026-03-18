import { Link } from "react-router";
import { Button } from "@/components/ui/button";

export default function NotFound() {
	return (
		<div className="mx-auto max-w-[800px] px-6 py-12 text-center">
			<h1 className="mb-2 text-4xl font-bold text-foreground">404</h1>
			<p className="mb-8 text-lg text-muted-foreground">Page not found</p>
			<Button asChild>
				<Link to="/">Go to Home</Link>
			</Button>
		</div>
	);
}
