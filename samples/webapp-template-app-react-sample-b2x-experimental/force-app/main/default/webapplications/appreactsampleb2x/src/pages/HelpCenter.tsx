import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function HelpCenter() {
	return (
		<div className="mx-auto max-w-[800px]">
			<h1 className="mb-6 text-2xl font-semibold text-primary">Help Center</h1>
			<Card className="mb-4">
				<CardHeader>
					<CardTitle>Frequently Asked Questions</CardTitle>
				</CardHeader>
				<CardContent>
					<p className="m-0 leading-relaxed text-foreground">
						Placeholder content for help and FAQs.
					</p>
				</CardContent>
			</Card>
			<Card>
				<CardHeader>
					<CardTitle>Contact Support</CardTitle>
				</CardHeader>
				<CardContent>
					<p className="m-0 leading-relaxed text-foreground">
						Reach out to the property management team for assistance.
					</p>
				</CardContent>
			</Card>
		</div>
	);
}
