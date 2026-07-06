BEGIN TRANSACTION;
CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
INSERT INTO "messages" VALUES(1,'debug_session','user','Your razor cut me, I will sue you! Horrible product.','2026-06-28 19:35:28');
INSERT INTO "messages" VALUES(2,'debug_session','assistant','I am very sorry to hear about your experience and understand your frustration. Regarding your query: Gillette Labs Exfoliating Razor features an exfoliating bar to remove dirt before blades pass. It uses stainless steel blades and a lubricating strip. Handle sharp blades with care. It is available at Walmart, CVS, and gillette.com. I have flagged this conversation for a human support representative who will follow up with you as soon as possible.','2026-06-28 19:35:28');
CREATE TABLE tickets (
                    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    tone TEXT NOT NULL,
                    urgency TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
INSERT INTO "tickets" VALUES(1,'debug_session','Your razor cut me, I will sue you! Horrible product.','Negative Tone (furious)','furious','medium','2026-06-28 19:35:23');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('tickets',1);
INSERT INTO "sqlite_sequence" VALUES('messages',2);
COMMIT;
