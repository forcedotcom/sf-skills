import { useState } from "react";
import { useNavigate } from "react-router";
import { SearchBar } from "../../components/SearchBar";
import { Button } from "../../../../components/ui/button";

export default function HomePage() {
	const navigate = useNavigate();
	const [text, setText] = useState("");

	const handleSubmit = (e: React.SyntheticEvent<HTMLFormElement>) => {
		e.preventDefault();
		const params = text ? `?q=${encodeURIComponent(text)}` : "";
		navigate(`/accounts${params}`);
	};

	return (
		<div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
			<div className="flex items-center gap-6 mb-6">
				<h1 className="text-2xl font-bold">Account Search</h1>
				<Button variant="outline" size="sm" onClick={() => navigate("/accounts")}>
					Browse All Accounts
				</Button>
			</div>
			<form onSubmit={handleSubmit} className="flex gap-2">
				<SearchBar
					placeholder="Search by name, phone, or industry..."
					value={text}
					handleChange={setText}
				/>
				<Button type="submit">Search</Button>
			</form>
		</div>
	);
}
