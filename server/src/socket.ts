import { Server, Socket } from "socket.io";
import mongoose from "mongoose";
import type { ChangeStream, ChangeStreamDocument, ResumeToken } from "mongodb";

type WatchTarget = {
  collectionName: string;
  event: string;
};

const WATCH_TARGETS: WatchTarget[] = [
  { collectionName: "line_items", event: "lineItemUpdated" },
  { collectionName: "appointments", event: "appointmentUpdated" },
  { collectionName: "unavailabilities", event: "unavailabilityUpdated" },
];

export function initSocket(io: Server, db: mongoose.Connection) {
  io.on("connection", (socket: Socket) => {
    console.log("✅ Client connected:", socket.id);
    socket.on("disconnect", () => {
      console.log("❌ Client disconnected:", socket.id);
    });
  });

  const activeStreams = new Map<string, ChangeStream>();

  const watchTarget = (
    target: WatchTarget,
    resumeToken?: ResumeToken,
    retryDelay = 1000
  ) => {
    const collection = db.collection(target.collectionName);

    let stream: ChangeStream;
    try {
      const pipeline: any[] = [
        // Optionally limit to relevant operations
        {
          $match: {
            operationType: { $in: ["insert", "update", "replace", "delete"] },
          },
        },
      ];
      const options: any = {
        fullDocument: "updateLookup", // ensure fullDocument is present on updates
      };
      if (resumeToken) options.resumeAfter = resumeToken;
      stream = collection.watch(pipeline, options);
    } catch (err) {
      const nextDelay = Math.min(retryDelay * 2, 30_000);
      console.error(
        `Failed to start change stream for ${target.collectionName}, retrying in ${nextDelay}ms`,
        err
      );
      setTimeout(() => watchTarget(target, resumeToken, nextDelay), nextDelay);
      return;
    }

    activeStreams.set(target.event, stream);

    let currentToken: ResumeToken | undefined = resumeToken;
    let backoffDelay = retryDelay;

    const scheduleRestart = (reason: string, err?: unknown) => {
      if (activeStreams.get(target.event) !== stream) return;
      if (err) {
        console.error(reason, err);
      } else {
        console.warn(reason);
      }

      activeStreams.delete(target.event);
      stream.close().catch(() => undefined);

      const nextDelay = Math.min(backoffDelay * 2, 30_000);
      setTimeout(() => watchTarget(target, currentToken, nextDelay), nextDelay);
    };

    stream.on("change", (change: ChangeStreamDocument) => {
      currentToken = change._id;
      backoffDelay = 1000;
      console.log(`📢 ${target.collectionName} updated:`, change);
      io.emit(target.event, change);
      // Emit an additional slim delta for line_items to simplify client consumption
      if (target.collectionName === "line_items") {
        try {
          const fullDoc: any = (change as any).fullDocument || {};
          const updatedFields: any = (change as any).updateDescription?.updatedFields || {};
          const slim = {
            line_item_id: fullDoc.line_item_id || fullDoc._id || (change as any).documentKey?._id,
            current_status: fullDoc.current_status || updatedFields.current_status,
            shoes: fullDoc.shoes || updatedFields.shoes,
            priority: fullDoc.priority || updatedFields.priority,
            transaction_id: fullDoc.transaction_id,
            operationType: (change as any).operationType,
            updatedFields,
            ts: Date.now(),
          };
            if (slim.line_item_id) {
              io.emit("lineItemDelta", slim);
            }
        } catch (e) {
          console.warn("Failed to emit lineItemDelta", e);
        }
      }
    });

    stream.on("error", (err) => {
      scheduleRestart(`Change stream error on ${target.collectionName}`, err);
    });

    stream.on("close", () => {
      scheduleRestart(`Change stream closed for ${target.collectionName}`);
    });
  };

  const openAllStreams = () => {
    WATCH_TARGETS.forEach((target) => {
      activeStreams.get(target.event)?.close().catch(() => undefined);
      activeStreams.delete(target.event);
      watchTarget(target);
    });
  };

  openAllStreams();

  db.on("disconnected", () => {
    console.warn("Mongo disconnected, closing change streams");
    activeStreams.forEach((stream) => stream.close().catch(() => undefined));
    activeStreams.clear();
  });

  db.on("reconnected", () => {
    console.info("Mongo reconnected, reopening change streams");
    openAllStreams();
  });
}
