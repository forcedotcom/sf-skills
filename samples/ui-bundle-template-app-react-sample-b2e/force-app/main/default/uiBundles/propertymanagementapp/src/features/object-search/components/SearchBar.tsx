import { Search } from "lucide-react";
import { Input } from "../../../components/ui/input";
import { cn } from "../../../lib/utils";

interface SearchBarProps extends React.ComponentProps<"div"> {
	value: string;
	handleChange: (value: string) => void;
	placeholder?: string;
	iconProps?: React.ComponentProps<typeof Search>;
	inputProps?: Omit<React.ComponentProps<typeof Input>, "value">;
}

export function SearchBar({
	value,
	handleChange,
	placeholder,
	className,
	iconProps,
	inputProps,
	...props
}: SearchBarProps) {
	return (
		<div className={cn("relative flex-1", className)} title={placeholder} {...props}>
			<Search
				{...iconProps}
				className={cn(
					"absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground",
					iconProps?.className,
				)}
			/>
			<Input
				type="text"
				value={value}
				onChange={(e) => handleChange(e.target.value)}
				placeholder={placeholder}
				{...inputProps}
				className={cn("pl-9", inputProps?.className)}
			/>
		</div>
	);
}
