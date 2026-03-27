/**
 * Renders a type-specific icon for maintenance requests (same approach as b2e MaintenanceTable).
 * Uses imported SVG assets; fallback to 🔧 when type has no icon.
 */
import PlumbingIcon from "@/assets/icons/plumbing.svg";
import HVACIcon from "@/assets/icons/hvac.svg";
import ElectricalIcon from "@/assets/icons/electrical.svg";
import AppliancesIcon from "@/assets/icons/appliances.svg";
import PestIcon from "@/assets/icons/pest.svg";

const issueIcons: Record<string, string> = {
	Plumbing: PlumbingIcon,
	HVAC: HVACIcon,
	Electrical: ElectricalIcon,
	Appliance: AppliancesIcon,
	Pest: PestIcon,
};

const issueIconColors: Record<string, string> = {
	Plumbing: "bg-teal-100",
	HVAC: "bg-teal-100",
	Electrical: "bg-teal-100",
	Appliance: "bg-teal-100",
	Pest: "bg-teal-100",
};

export function MaintenanceRequestIcon({ type }: { type: string | null }) {
	const issueType = type?.trim() ?? "";
	const iconSrc = issueIcons[issueType];
	const bgClass = issueIconColors[issueType] ?? "bg-teal-100";

	return (
		<div
			className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg ${bgClass}`}
			aria-hidden
		>
			{iconSrc ? (
				<img src={iconSrc} alt={issueType || "Request"} className="h-6 w-6" />
			) : (
				<span className="text-2xl" aria-hidden>
					🔧
				</span>
			)}
		</div>
	);
}
