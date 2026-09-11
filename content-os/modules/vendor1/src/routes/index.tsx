import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { PlanningConsole } from "@/components/planning-console";

export const Route = createFileRoute("/")({
  ssr: false,
  component: Home,
});

function Home() {
  const token = useMemo(() => "thbison-test-token-aaaaaaaa", []);
  const [mode] = useState("MOCK / TEST_ONLY");
  return (
    <PlanningConsole
      token={token}
      modeLabel={mode}
      contract="1.0.0"
    />
  );
}
