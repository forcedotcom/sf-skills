import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";

const listings = [
	{
		id: "1",
		name: "Verdana Apartments",
		address: "301 Bryant St, San Francisco, CA 94107",
		price: "$4,600+",
		beds: "2 Beds",
		phone: "(650) 440-1111",
	},
	{
		id: "2",
		name: "South Beach Lofts",
		address: "250 Brannan St, San Francisco, CA 94107",
		price: "$5,379+",
		beds: "2 Beds",
		phone: "(650) 555-0123",
	},
];

export default function PropertyListings() {
	return (
		<div className="grid min-h-[500px] grid-cols-1 gap-6 lg:grid-cols-[320px_1fr]">
			<div className="min-h-[400px] rounded-xl bg-muted" aria-label="Map placeholder" />
			<div>
				<div className="mb-4 flex flex-wrap gap-3">
					<Input
						type="text"
						defaultValue="San Francisco, CA"
						className="min-w-[200px] flex-1 flex-[1_1_200px] rounded-xl"
					/>
					<Button
						variant="outline"
						className="cursor-pointer rounded-xl transition-colors duration-200"
					>
						Price
					</Button>
					<Button
						variant="outline"
						className="cursor-pointer rounded-xl transition-colors duration-200"
					>
						Beds/Bath
					</Button>
					<Button className="cursor-pointer rounded-xl transition-colors duration-200">
						All Filters
					</Button>
				</div>
				<h2 className="mb-1 text-lg font-semibold text-foreground">
					2 Bedroom Apartments for Rent in San Francisco CA
				</h2>
				<p className="mb-4 text-sm text-muted-foreground">1,181 Rentals Available</p>
				<div className="space-y-4">
					{listings.map((p) => (
						<Card key={p.name} className="rounded-2xl shadow-md">
							<CardContent className="flex gap-4 p-4">
								<Link
									to={`/property/${p.id}`}
									className="relative block size-[120px] sm:size-[200px] shrink-0 cursor-pointer rounded-xl bg-muted transition-opacity duration-200 hover:opacity-95"
								>
									<span className="absolute left-2 top-2 rounded-full bg-violet-600 px-2 py-0.5 text-xs font-medium text-white">
										Virtual Tours
									</span>
								</Link>
								<div className="min-w-0 flex-1">
									<h3 className="mb-1 text-base font-semibold">
										<Link
											to={`/property/${p.id}`}
											className="cursor-pointer text-primary no-underline transition-colors duration-200 hover:underline"
										>
											{p.name}
										</Link>
									</h3>
									<p className="mb-2 text-sm text-muted-foreground">{p.address}</p>
									<p className="mb-1 text-sm text-foreground">
										{p.price} {p.beds}
									</p>
									<p className="mb-2 text-sm text-muted-foreground">
										In Unit Washer & Dryer, Pets Allowed, Fitness Center
									</p>
									<p className="mb-2 text-sm text-primary">{p.phone}</p>
									<Button
										asChild
										size="sm"
										className="cursor-pointer rounded-xl transition-colors duration-200"
									>
										<Link to={`/application?listingId=${encodeURIComponent(p.id)}`}>Apply</Link>
									</Button>
								</div>
							</CardContent>
						</Card>
					))}
				</div>
			</div>
		</div>
	);
}
