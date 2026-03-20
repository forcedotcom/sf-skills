import { Link, useNavigate } from "react-router";
import { useRef, useState, type ChangeEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { usePropertyListingSearch } from "@/hooks/usePropertyListingSearch";
import {
	usePropertyPrimaryImages,
	getPropertyIdFromRecord,
} from "@/hooks/usePropertyPrimaryImages";
import { usePropertyAddresses } from "@/hooks/usePropertyAddresses";
import { usePropertyListingAmenities } from "@/hooks/usePropertyListingAmenities";
import PropertyListingCard from "@/components/PropertyListingCard";
import { createNewsletterLead } from "@/api/leadApi";
import {
	Phone,
	Send,
	ChevronDown,
	ChevronUp,
	MessageCircle,
	HelpCircle,
	Facebook,
	Instagram,
	Twitter,
} from "lucide-react";

const HERO_IMAGE = "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1200&q=85";
const CITY_IMAGE = "https://images.unsplash.com/photo-1514565131-fce0801e5785?w=800&q=85";
const RELAX_IMAGE = "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=600&q=85";

const FEATURED_PAGE_SIZE = 3;

const FAQ_ITEMS = [
	{
		q: "How do I apply for an apartment?",
		a: "Applications can be completed online directly through our website at your convenience. Go to Property Search, choose a listing, and click Apply to start. If you need assistance, please reach out via Contact Us.",
	},
	{
		q: "How long does the application approval process take?",
		a: "Most applications are reviewed within 2–3 business days. You'll receive an email once your application has been processed.",
	},
	{
		q: "Do you offer flexible lease terms?",
		a: "Yes. Many of our properties offer 1-, 6-, or 12-month lease terms. Check the listing details or contact us for options.",
	},
	{
		q: "What is the penalty for breaking a lease early?",
		a: "Early termination terms vary by property. Please review your lease agreement or contact the property manager for details.",
	},
	{
		q: "What are the income and credit qualifications?",
		a: "Requirements vary by property. Typical guidelines include income of at least 3x monthly rent and a credit check. See each listing for specifics.",
	},
];

export default function Home() {
	const searchInputRef = useRef<HTMLInputElement>(null);
	const navigate = useNavigate();
	const [faqOpen, setFaqOpen] = useState<number | null>(0);
	const [footerEmail, setFooterEmail] = useState("");
	const [newsletterSubmitting, setNewsletterSubmitting] = useState(false);
	const [newsletterMessage, setNewsletterMessage] = useState<{
		type: "success" | "error";
		text: string;
	} | null>(null);

	const { results: featuredResults } = usePropertyListingSearch("", FEATURED_PAGE_SIZE, "0");
	const primaryImagesMap = usePropertyPrimaryImages(featuredResults);
	const propertyAddressMap = usePropertyAddresses(featuredResults);
	const amenitiesMap = usePropertyListingAmenities(featuredResults);

	const handleFindHome = (e: React.FormEvent) => {
		e.preventDefault();
		const q = searchInputRef.current?.value?.trim() ?? "";
		navigate(q ? `/properties?search=${encodeURIComponent(q)}` : "/properties");
	};

	const handleFooterSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		const email = footerEmail.trim();
		if (!email) return;
		setNewsletterMessage(null);
		setNewsletterSubmitting(true);
		try {
			await createNewsletterLead(email);
			setFooterEmail("");
			setNewsletterMessage({ type: "success", text: "Thanks! You’re subscribed." });
		} catch {
			setNewsletterMessage({ type: "error", text: "Something went wrong. Try again later." });
		} finally {
			setNewsletterSubmitting(false);
		}
	};

	const validFeatured = featuredResults.filter((r) => r?.record?.id);

	return (
		<div className="space-y-0">
			{/* ——— Hero ——— */}
			<div className="relative w-full overflow-hidden rounded-2xl">
				<div className="relative aspect-[21/9] min-h-[280px] w-full md:aspect-[3/1] md:min-h-[320px]">
					<img
						src={HERO_IMAGE}
						alt=""
						className="h-full w-full object-cover"
						loading="eager"
						fetchPriority="high"
					/>
					<div className="absolute inset-0 bg-black/40" />
					<div className="absolute inset-0 flex flex-col items-center justify-center gap-6 px-4">
						<div className="w-full max-w-2xl text-center">
							<p className="mb-2 text-xs font-medium uppercase tracking-[0.2em] text-white/80">
								The Zen Way to Lease
							</p>
							<h1 className="mb-2 text-3xl font-semibold tracking-tight text-white drop-shadow-md md:text-4xl lg:text-5xl">
								Your Dream Place Starts Here
							</h1>
							<p className="mb-6 text-base text-white/90 md:text-lg">
								Search properties, manage applications, and move in with ease.
							</p>
						</div>
						<form
							onSubmit={handleFindHome}
							className="flex w-full max-w-xl flex-col gap-2 sm:flex-row sm:rounded-lg"
						>
							<Input
								ref={searchInputRef}
								type="text"
								name="search"
								placeholder="Search by address, city, or zip code"
								aria-label="Search properties"
								className="min-h-12 flex-1 rounded-lg border-0 bg-white/95 px-4 text-foreground shadow-lg placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-white"
							/>
							<Button
								type="submit"
								size="lg"
								className="min-h-12 shrink-0 cursor-pointer rounded-xl bg-primary px-8 font-medium text-primary-foreground shadow-md transition-colors duration-200 hover:bg-primary/90"
							>
								Find Home
							</Button>
						</form>
						<p className="text-sm text-white/80">
							or{" "}
							<Link
								to="/properties"
								className="cursor-pointer font-medium text-white underline underline-offset-2 transition-colors duration-200 hover:no-underline"
							>
								browse all properties
							</Link>
						</p>
					</div>
				</div>
			</div>

			{/* ——— Featured Properties ——— */}
			<section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-violet-100/80 to-pink-100/80 px-4 py-12 md:px-6">
				<div className="relative mx-auto max-w-6xl">
					<h2 className="mb-8 text-2xl font-bold tracking-tight text-violet-900 md:text-3xl">
						Featured Properties
					</h2>
					{validFeatured.length > 0 ? (
						<div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
							{validFeatured.map((item, index) => {
								const record = item.record;
								const propertyId = getPropertyIdFromRecord(record);
								const imageUrl = propertyId ? (primaryImagesMap[propertyId] ?? null) : null;
								const address = propertyId ? (propertyAddressMap[propertyId] ?? null) : null;
								const amenities = propertyId ? (amenitiesMap[propertyId] ?? null) : null;
								return (
									<div key={record.id ?? index} className="min-h-0">
										<PropertyListingCard
											record={record}
											imageUrl={imageUrl}
											address={address}
											amenities={amenities ?? undefined}
										/>
									</div>
								);
							})}
						</div>
					) : (
						<div className="rounded-xl bg-white/60 px-6 py-10 text-center text-muted-foreground">
							<p>No featured properties at the moment.</p>
							<Button asChild className="mt-3">
								<Link to="/properties">Browse all properties</Link>
							</Button>
						</div>
					)}
				</div>
			</section>

			{/* ——— Stats / Trust ——— */}
			<section className="grid min-h-[320px] grid-cols-1 overflow-hidden rounded-2xl bg-card shadow-md md:grid-cols-2">
				<div className="relative min-h-[240px] md:min-h-0">
					<img src={CITY_IMAGE} alt="" className="h-full w-full object-cover" />
					<div className="absolute inset-0 bg-gradient-to-r from-black/20 to-transparent md:from-transparent" />
				</div>
				<div className="flex flex-col justify-center gap-6 bg-gradient-to-br from-amber-50 to-stone-100 px-6 py-10 md:px-10">
					<div className="grid gap-4 sm:grid-cols-2">
						{[
							{ value: "20K+", label: "Satisfied tenants and still counting" },
							{ value: "10+", label: "Years of experience you can count on" },
							{ value: "15+", label: "Award-winning service, trusted results" },
							{ value: "5K+", label: "Happy tenants and clients" },
						].map((stat, i) => (
							<div key={i} className="rounded-xl bg-white/80 px-4 py-4 shadow-sm">
								<p className="text-2xl font-bold text-teal-800">{stat.value}</p>
								<p className="text-sm text-muted-foreground">{stat.label}</p>
							</div>
						))}
					</div>
					<div className="flex flex-wrap items-center gap-4">
						<Button
							asChild
							size="lg"
							className="cursor-pointer rounded-xl bg-primary transition-colors duration-200 hover:bg-primary/90"
						>
							<Link to="/contact">More About Us</Link>
						</Button>
						<a
							href="tel:18005550120"
							className="inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-foreground transition-colors duration-200 hover:underline"
						>
							<Phone className="size-4" />
							Talk to an Agent 1.800.555.0120
						</a>
					</div>
				</div>
			</section>

			{/* ——— Testimonials ——— */}
			<section className="overflow-hidden rounded-2xl bg-gradient-to-br from-violet-100/80 to-pink-100/80 px-4 py-12 md:px-6">
				<div className="relative mx-auto grid max-w-6xl gap-8 lg:grid-cols-3">
					<div className="lg:col-span-2">
						<h2 className="mb-8 text-2xl font-bold tracking-tight text-violet-900 md:text-3xl">
							What Our Clients Are Saying
						</h2>
						<div className="grid gap-6 sm:grid-cols-2">
							<Card className="border-0 bg-white/80 shadow-md">
								<CardContent className="p-6">
									<h3 className="mb-2 font-semibold text-foreground">Game-changing convenience</h3>
									<p className="mb-4 text-sm text-muted-foreground">
										Applying online was so easy. I had a response within a day and moved in the
										following week. Highly recommend.
									</p>
									<p className="text-sm font-medium text-foreground">— Des M.</p>
								</CardContent>
							</Card>
							<Card className="border-0 bg-white/80 shadow-md">
								<CardContent className="p-6">
									<h3 className="mb-2 font-semibold text-foreground">
										Highly personalized experience
									</h3>
									<p className="mb-4 text-sm text-muted-foreground">
										The team was responsive and helped me find exactly what I was looking for. The
										whole process felt smooth and professional.
									</p>
									<p className="text-sm font-medium text-foreground">— Zoe T.</p>
								</CardContent>
							</Card>
						</div>
					</div>
					<div className="relative hidden overflow-hidden rounded-2xl lg:block">
						<img src={RELAX_IMAGE} alt="" className="h-full w-full object-cover" />
						<div className="absolute inset-0 flex items-end bg-gradient-to-t from-black/60 to-transparent p-6">
							<p className="text-lg font-semibold text-white">
								Relax and Get Zen. Your Home Awaits.
							</p>
						</div>
					</div>
				</div>
			</section>

			{/* ——— AI / Peace of Mind ——— */}
			<section className="rounded-2xl bg-teal-50 px-4 py-12 md:px-6">
				<div className="mx-auto max-w-3xl text-center">
					<h2 className="mb-3 text-2xl font-bold tracking-tight text-teal-900 md:text-3xl">
						AI-Powered, Peace of Mind
					</h2>
					<p className="mb-8 text-muted-foreground">
						From inquiry to move-in: our AI assists with the hard part so you can focus on living.
					</p>
					<div className="flex flex-wrap justify-center gap-3">
						<Button asChild variant="secondary" size="lg" className="rounded-full">
							<Link to="/properties">Find My Home</Link>
						</Button>
						<Button asChild variant="outline" size="lg" className="rounded-full gap-2">
							<Link to="/contact">
								<MessageCircle className="size-4" />
								Contact
							</Link>
						</Button>
						<Button asChild variant="ghost" size="lg" className="rounded-full gap-2">
							<Link to="/contact">
								<HelpCircle className="size-4" />
								Help
							</Link>
						</Button>
					</div>
				</div>
			</section>

			{/* ——— FAQ ——— */}
			<section className="rounded-2xl bg-teal-50/80 px-4 py-12 md:px-6">
				<div className="mx-auto max-w-3xl">
					<h2 className="mb-8 text-2xl font-bold tracking-tight text-teal-900 md:text-3xl">
						Frequently Asked Questions
					</h2>
					<div className="space-y-2">
						{FAQ_ITEMS.map((item, index) => (
							<div
								key={index}
								className="overflow-hidden rounded-xl border border-teal-100 bg-white shadow-sm"
							>
								<button
									type="button"
									onClick={() => setFaqOpen(faqOpen === index ? null : index)}
									className="flex w-full cursor-pointer items-center justify-between gap-4 px-5 py-4 text-left font-medium text-foreground transition-colors duration-200 hover:bg-muted/50"
								>
									<span>{item.q}</span>
									{faqOpen === index ? (
										<ChevronUp className="size-5 shrink-0 text-muted-foreground" />
									) : (
										<ChevronDown className="size-5 shrink-0 text-muted-foreground" />
									)}
								</button>
								{faqOpen === index && (
									<div className="border-t border-teal-100 px-5 py-4 text-sm text-muted-foreground">
										{item.a}
									</div>
								)}
							</div>
						))}
					</div>
				</div>
			</section>

			{/* ——— Footer ——— */}
			<footer className="overflow-hidden rounded-2xl bg-teal-800 text-teal-100">
				<div className="grid gap-8 px-6 py-10 md:grid-cols-2 lg:grid-cols-4">
					<div className="lg:col-span-2">
						<p className="mb-4 text-xl font-semibold tracking-wide text-white">ZENLEASE</p>
						<p className="mb-4 text-sm text-teal-200">Stay updated with new listings and tips.</p>
						<form onSubmit={handleFooterSubmit} className="flex flex-col gap-2">
							<div className="flex gap-2">
								<Input
									type="email"
									placeholder="Enter your email"
									value={footerEmail}
									onChange={(e: ChangeEvent<HTMLInputElement>) => setFooterEmail(e.target.value)}
									disabled={newsletterSubmitting}
									className="max-w-xs border-teal-600 bg-teal-900/50 text-white placeholder:text-teal-300"
									aria-label="Email for updates"
								/>
								<Button
									type="submit"
									size="icon"
									className="shrink-0 bg-teal-600 hover:bg-teal-700"
									disabled={newsletterSubmitting}
								>
									<Send className="size-4" aria-hidden />
								</Button>
							</div>
							{newsletterMessage && (
								<p
									className={
										newsletterMessage.type === "success" ? "text-teal-200" : "text-red-300"
									}
								>
									{newsletterMessage.text}
								</p>
							)}
						</form>
					</div>
					<div>
						<h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-white">
							Explore
						</h4>
						<ul className="space-y-2 text-sm">
							<li>
								<Link to="/" className="text-teal-200 hover:text-white">
									Home
								</Link>
							</li>
							<li>
								<Link to="/properties" className="text-teal-200 hover:text-white">
									Property Search
								</Link>
							</li>
							<li>
								<Link to="/application" className="text-teal-200 hover:text-white">
									Apply
								</Link>
							</li>
						</ul>
					</div>
					<div>
						<h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-white">
							Support
						</h4>
						<ul className="space-y-2 text-sm">
							<li>
								<Link to="/contact" className="text-teal-200 hover:text-white">
									Contact Us
								</Link>
							</li>
							<li>
								<Link to="/maintenance" className="text-teal-200 hover:text-white">
									Maintenance
								</Link>
							</li>
							<li>
								<a href="tel:18005550120" className="text-teal-200 hover:text-white">
									Talk to an agent
								</a>
							</li>
						</ul>
					</div>
				</div>
				<div className="flex flex-col items-center justify-between gap-4 border-t border-teal-700 px-6 py-4 sm:flex-row">
					<p className="text-xs text-teal-300">
						© {new Date().getFullYear()} ZENLEASE. All rights reserved. Terms & Conditions
					</p>
					<div className="flex gap-4">
						<a href="#" className="text-teal-300 hover:text-white" aria-label="Facebook">
							<Facebook className="size-5" aria-hidden />
						</a>
						<a href="#" className="text-teal-300 hover:text-white" aria-label="Instagram">
							<Instagram className="size-5" aria-hidden />
						</a>
						<a href="#" className="text-teal-300 hover:text-white" aria-label="Twitter">
							<Twitter className="size-5" aria-hidden />
						</a>
					</div>
				</div>
			</footer>
		</div>
	);
}
