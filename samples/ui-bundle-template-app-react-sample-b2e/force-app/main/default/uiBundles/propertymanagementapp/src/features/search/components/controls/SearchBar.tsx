import { Search } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Input } from "../../../../components/ui/input";
import { debounce } from "../../utils/debounce";

const TYPE_DEBOUNCE_MS = 250;

interface SearchBarProps {
	value: string;
	onChange: (next: string) => void;
	placeholder?: string;
	className?: string;
}

/**
 * Debounced text input for the global `q` term. Keeps a local `draft` so
 * keystrokes feel responsive while the upstream `onChange` is rate-limited.
 */
export function SearchBar({ value, onChange, placeholder = "Search…", className }: SearchBarProps) {
	const [draft, setDraft] = useState(value);
	const onChangeRef = useRef(onChange);
	useEffect(() => {
		onChangeRef.current = onChange;
	});

	// Build the debounced caller in a mount effect, not during render: creating it
	// inline would read onChangeRef.current at render time (react-hooks/refs). It
	// stays a single stable instance and always calls the latest onChange via the ref.
	const debouncedRef = useRef<((next: string) => void) | undefined>(undefined);
	useEffect(() => {
		debouncedRef.current = debounce((next: string) => onChangeRef.current(next), TYPE_DEBOUNCE_MS);
	}, []);

	// External value can change (URL restore, reset). Keep draft in sync.
	useEffect(() => {
		setDraft(value);
	}, [value]);

	return (
		<div className={`relative flex-1 ${className ?? ""}`}>
			<Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
			<Input
				type="text"
				value={draft}
				onChange={(e) => {
					setDraft(e.target.value);
					debouncedRef.current?.(e.target.value);
				}}
				placeholder={placeholder}
				className="pl-9"
				aria-label="Unified search"
			/>
		</div>
	);
}
