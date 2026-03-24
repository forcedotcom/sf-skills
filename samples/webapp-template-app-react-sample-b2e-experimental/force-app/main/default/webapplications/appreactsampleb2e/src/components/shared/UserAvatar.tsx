import React from "react";

interface UserAvatarProps {
	name: string;
	imageUrl?: string;
	size?: "sm" | "md" | "lg";
}

export const UserAvatar: React.FC<UserAvatarProps> = ({ name, imageUrl, size = "md" }) => {
	const sizeClasses = {
		sm: "w-8 h-8 text-xs",
		md: "w-10 h-10 text-sm",
		lg: "w-12 h-12 text-base",
	};

	const getInitials = (name: string) => {
		const parts = name.trim().split(" ");
		if (parts.length >= 2) {
			return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
		}
		return name.substring(0, 2).toUpperCase();
	};

	return (
		<div
			className={`${sizeClasses[size]} rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0 overflow-hidden`}
		>
			{imageUrl ? (
				<img src={imageUrl} alt={name} className="w-full h-full object-cover" />
			) : (
				<span className="font-medium text-gray-700">{getInitials(name)}</span>
			)}
		</div>
	);
};
