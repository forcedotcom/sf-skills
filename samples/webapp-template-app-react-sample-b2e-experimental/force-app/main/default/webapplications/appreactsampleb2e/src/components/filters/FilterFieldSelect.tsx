import * as React from "react";
import type { Filter } from "../../features/global-search/types/filters/filters";
import { ALL_PLACEHOLDER_VALUE, MULTI_VALUE_SEP } from "../../lib/filterUtils";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../components/ui/select";

const TRIGGER_CLASS =
	"h-9 rounded-md border border-gray-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent min-w-[140px] data-[size=default]:h-9";

interface FilterFieldSelectProps {
	filter: Filter;
	options: { label?: string; value: string }[];
	value: string;
	onChange: (value: string) => void;
	multiSelect?: boolean;
}

function FilterFieldSelectSingle({
	filter,
	options,
	value,
	onChange,
}: Omit<FilterFieldSelectProps, "multiSelect">) {
	const label = filter.label || filter.targetFieldPath;
	const placeholder = filter.attributes?.placeholder || "All";
	const id = `filter-${filter.targetFieldPath}`;
	return (
		<div className="flex flex-col gap-1.5 min-w-[160px]" role="group" aria-label={label}>
			<label htmlFor={id} className="text-sm font-medium text-gray-700 whitespace-nowrap">
				{label}
			</label>
			<Select
				value={value || ALL_PLACEHOLDER_VALUE}
				onValueChange={(v) => onChange(v === ALL_PLACEHOLDER_VALUE ? "" : (v ?? ""))}
			>
				<SelectTrigger id={id} className={TRIGGER_CLASS} size="default" aria-label={label}>
					<SelectValue placeholder={placeholder} />
				</SelectTrigger>
				<SelectContent>
					<SelectItem value={ALL_PLACEHOLDER_VALUE}>{placeholder}</SelectItem>
					{options.map((opt) => (
						<SelectItem key={opt.value} value={opt.value}>
							{opt.label || opt.value}
						</SelectItem>
					))}
				</SelectContent>
			</Select>
		</div>
	);
}

function FilterFieldMultiSelect({
	filter,
	options,
	value,
	onChange,
}: Omit<FilterFieldSelectProps, "multiSelect">) {
	const label = filter.label || filter.targetFieldPath;
	const selected = value ? value.split(MULTI_VALUE_SEP).filter(Boolean) : [];
	const [open, setOpen] = React.useState(false);
	const triggerRef = React.useRef<HTMLButtonElement>(null);
	const panelRef = React.useRef<HTMLDivElement>(null);

	React.useEffect(() => {
		if (!open) return;
		const close = (e: MouseEvent) => {
			if (
				triggerRef.current?.contains(e.target as Node) ||
				panelRef.current?.contains(e.target as Node)
			)
				return;
			setOpen(false);
		};
		const handleKeyDown = (e: KeyboardEvent) => {
			if (e.key === "Escape") setOpen(false);
		};
		document.addEventListener("mousedown", close);
		document.addEventListener("keydown", handleKeyDown);
		return () => {
			document.removeEventListener("mousedown", close);
			document.removeEventListener("keydown", handleKeyDown);
		};
	}, [open]);

	const toggle = (optValue: string) => {
		const next = selected.includes(optValue)
			? selected.filter((v) => v !== optValue)
			: [...selected, optValue];
		onChange(next.join(MULTI_VALUE_SEP));
	};

	const displayText =
		selected.length === 0
			? filter.attributes?.placeholder || "All"
			: selected.length === 1
				? options.find((o) => o.value === selected[0])?.label || selected[0]
				: `${selected.length} selected`;

	return (
		<div className="flex flex-col gap-1.5 min-w-[160px]" role="group" aria-label={label}>
			<label className="text-sm font-medium text-gray-700 whitespace-nowrap">{label}</label>
			<div className="relative">
				<button
					ref={triggerRef}
					type="button"
					onClick={() => setOpen((o) => !o)}
					className={`${TRIGGER_CLASS} w-full flex items-center justify-between gap-2 px-3 text-left`}
					aria-label={label}
					aria-expanded={open}
					aria-haspopup="listbox"
				>
					<span className="truncate">{displayText}</span>
					<svg
						className={`h-4 w-4 shrink-0 text-gray-500 transition-transform ${open ? "rotate-180" : ""}`}
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						aria-hidden
					>
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
					</svg>
				</button>
				{open && (
					<div
						ref={panelRef}
						role="listbox"
						className="absolute top-full left-0 z-50 mt-1 min-w-[var(--radix-select-trigger-width)] rounded-lg border border-gray-200 bg-white py-1 shadow-md max-h-60 overflow-auto"
					>
						{options.map((opt) => {
							const isSelected = selected.includes(opt.value);
							return (
								<button
									key={opt.value}
									type="button"
									role="option"
									aria-selected={isSelected}
									onClick={() => toggle(opt.value)}
									className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-gray-100 focus:bg-gray-100 focus:outline-none"
								>
									<span
										className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
											isSelected ? "bg-purple-600 border-purple-600" : "border-gray-300"
										}`}
									>
										{isSelected && (
											<svg
												className="h-3 w-3 text-white"
												viewBox="0 0 12 12"
												fill="none"
												stroke="currentColor"
												strokeWidth="2"
												strokeLinecap="round"
												strokeLinejoin="round"
											>
												<polyline points="2,6 5,9 10,3" />
											</svg>
										)}
									</span>
									{opt.label || opt.value}
								</button>
							);
						})}
					</div>
				)}
			</div>
		</div>
	);
}

export function FilterFieldSelect({
	filter,
	options,
	value,
	onChange,
	multiSelect = true,
}: FilterFieldSelectProps) {
	if (multiSelect) {
		return (
			<FilterFieldMultiSelect filter={filter} options={options} value={value} onChange={onChange} />
		);
	}
	return (
		<FilterFieldSelectSingle filter={filter} options={options} value={value} onChange={onChange} />
	);
}
