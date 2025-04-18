import { memo, useEffect, useState } from "react";
import { Handle, NodeProps, Position } from "reactflow";
import { getDestinationIconUrl } from "@/lib/utils/icons";
import { apiClient } from "@/lib/api";
import { Connection } from "@/components/sync/dag";
import { cn } from "@/lib/utils";
import { toast } from "@/components/ui/use-toast";

export const DestinationNode = memo(({ data, selected, ...props }: NodeProps) => {
  const [connection, setConnection] = useState<Connection | null>(null);

  useEffect(() => {
    const fetchConnection = async () => {
      if (!data.connection_id) return;

      try {
        const resp = await apiClient.get(`/connections/detail/${data.connection_id}`);
        if (!resp.ok) throw new Error("Failed to fetch connection details");
        const connData = await resp.json();
        setConnection(connData);
      } catch (error) {
        console.error("Error fetching connection:", error);
        toast({
          variant: "destructive",
          title: "Failed to load connection details",
          description: "Please try refreshing the page",
        });
      }
    };

    fetchConnection();
  }, [data.connection_id]);

  // Use qdrant_native as default shortName when no connection
  const shortName = connection?.short_name || (data.connection_id ? data.shortName : "qdrant");
  const name = connection?.name || data.name || "Native Qdrant";

  return (
    <div className="w-24 h-24">
      <div
        className={cn(
          "w-full h-full flex flex-col bg-background/80 backdrop-blur-sm",
          "border-2 transition-colors duration-200 cursor-pointer",
          "border-muted-foreground/50 hover:border-primary rounded-l-lg rounded-r-2xl",
          selected ? "border-primary shadow-sm shadow-primary/20" : ""
        )}
      >
        <Handle
          type="target"
          position={Position.Left}
          className="w-3 h-3 -ml-[3px] border border-background bg-muted-foreground"
        />

        <div className="w-full h-full flex items-center justify-center">
          <div className="w-16 h-16 flex flex-col items-center">
            <img
              src={getDestinationIconUrl("qdrant")}
              alt="Native Qdrant"
              className="w-12 h-12 object-contain"
            />
            <span className="text-[10px] mt-2 text-center">Qdrant</span>
          </div>
        </div>
      </div>
      <div className="absolute -bottom-7 left-1/2 -translate-x-1/2 whitespace-nowrap">
        <span className="text-sm font-semibold text-foreground text-center">Native Qdrant</span>
      </div>
    </div>
  );
});

DestinationNode.displayName = "DestinationNode";
