BEGIN TRANSACTION;
CREATE TABLE messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
INSERT INTO "messages" VALUES(1,'session_puzjuq7s0q','user','What are the ingredients in Tide Hygienic Clean?','2026-06-29 12:32:26');
INSERT INTO "messages" VALUES(2,'session_puzjuq7s0q','assistant','Thank you for reaching out! The ingredients in Tide Hygienic Clean Heavy Duty 10X are Sodium Alcoholethoxy Sulfate, Linear Alkylbenzene Sulfonate, Propylene Glycol, Sodium Borate, and Water.','2026-06-29 12:32:26');
INSERT INTO "messages" VALUES(3,'session_puzjuq7s0q','user','i am rishab ,i have a sensitive skin suggest a facewash','2026-06-29 16:54:12');
INSERT INTO "messages" VALUES(4,'session_puzjuq7s0q','assistant','Hi Rishab,

Thank you for reaching out!

Based on the product information I have, I am unable to suggest a face wash at this time. I can only provide details on the Olay Regenerist Whip Active Moisturizer.','2026-06-29 16:54:12');
INSERT INTO "messages" VALUES(5,'session_puzjuq7s0q','user','whoo am i?','2026-06-29 16:54:33');
INSERT INTO "messages" VALUES(6,'session_puzjuq7s0q','assistant','Thank you for reaching out!

I appreciate you connecting with us. However, I am designed to assist with questions related to P&G products and services. I cannot answer personal questions like "whoo am i?" as it is not related to the product information I have.

If you have any questions about our products, please feel free to ask!','2026-06-29 16:54:33');
INSERT INTO "messages" VALUES(7,'session_puzjuq7s0q','user','whats my skin type','2026-06-29 16:54:56');
INSERT INTO "messages" VALUES(8,'session_puzjuq7s0q','assistant','Regarding your query: Tide Hygienic Clean Heavy Duty 10X is designed for heavy-duty cleaning and removing grease. It contains Sodium Alcoholethoxy Sulfate and Sodium Borate. Keep out of reach of children. It is available at Walmart and Target.','2026-06-29 16:54:56');
INSERT INTO "messages" VALUES(9,'session_puzjuq7s0q','user','hey','2026-07-04 10:29:29');
INSERT INTO "messages" VALUES(10,'session_puzjuq7s0q','assistant','Regarding your query: Tide Hygienic Clean Heavy Duty 10X is designed for heavy-duty cleaning and removing grease. It contains Sodium Alcoholethoxy Sulfate and Sodium Borate. Keep out of reach of children. It is available at Walmart and Target.','2026-07-04 10:29:29');
INSERT INTO "messages" VALUES(11,'session_n7686eg4t7m','user','hey ','2026-07-04 10:29:58');
INSERT INTO "messages" VALUES(12,'session_n7686eg4t7m','assistant','I''m happy to help you find the right P&G product. Could you tell me a bit more about what you''re looking for (e.g. skin care, laundry care, baby diapers, or shaving)?','2026-07-04 10:29:58');
INSERT INTO "messages" VALUES(13,'session_n7686eg4t7m','user','i am rishab i have a comination skin (oily and dry) what kind of face wash should i buy?','2026-07-04 10:31:38');
INSERT INTO "messages" VALUES(14,'session_n7686eg4t7m','assistant','Regarding your query: Tide Hygienic Clean Heavy Duty 10X is designed for heavy-duty cleaning and removing grease. It contains Sodium Alcoholethoxy Sulfate and Sodium Borate. Keep out of reach of children. It is available at Walmart and Target.','2026-07-04 10:31:38');
INSERT INTO "messages" VALUES(15,'session_n7686eg4t7m','user','my baby has rashes','2026-07-04 10:32:09');
INSERT INTO "messages" VALUES(16,'session_n7686eg4t7m','assistant','Your safety is our top priority. Please stop using the product immediately. If someone ingested the product or is experiencing a severe reaction, contact a healthcare professional or Poison Control right away. Regarding your query: Pampers Splashers Disposable Swim Diapers are waterproof swim diapers that do not swell in water. They are made of Polypropylene and Polyethylene. Diapers are flammable, so keep them away from open flame. You can buy them at Target, Walgreens, and Amazon. I have flagged this conversation for a human support representative who will follow up with you as soon as possible.','2026-07-04 10:32:09');
INSERT INTO "messages" VALUES(17,'session_1c2d1pfdwwy','user','hi','2026-07-04 17:24:36');
INSERT INTO "messages" VALUES(18,'session_1c2d1pfdwwy','assistant','Your safety is our top priority. Please stop using the product immediately. If someone ingested the product or is experiencing a severe reaction, contact a healthcare professional or Poison Control right away. I''m happy to help you find the right P&G product. Could you tell me a bit more about what you''re looking for (e.g. skin care, laundry care, baby diapers, or shaving)? I have flagged this conversation for a human support representative who will follow up with you as soon as possible.','2026-07-04 17:24:36');
INSERT INTO "messages" VALUES(19,'session_q56ppr5pgl','user','hey','2026-07-04 18:49:31');
INSERT INTO "messages" VALUES(20,'session_q56ppr5pgl','assistant','Your safety is our top priority. Please stop using the product immediately. If someone ingested the product or is experiencing a severe reaction, contact a healthcare professional or Poison Control right away. I''m happy to help you find the right P&G product. Could you tell me a bit more about what you''re looking for (e.g. skin care, laundry care, baby diapers, or shaving)? I have flagged this conversation for a human support representative who will follow up with you as soon as possible.','2026-07-04 18:49:31');
INSERT INTO "messages" VALUES(21,'session_q56ppr5pgl','user','can you suggest a fash wash','2026-07-04 18:50:26');
INSERT INTO "messages" VALUES(22,'session_q56ppr5pgl','assistant','Regarding your query: Tide Hygienic Clean Heavy Duty 10X is designed for heavy-duty cleaning and removing grease. It contains Sodium Alcoholethoxy Sulfate and Sodium Borate. Keep out of reach of children. It is available at Walmart and Target.','2026-07-04 18:50:26');
INSERT INTO "messages" VALUES(23,'session_th7oir1nmok','user','I have sensitive skin. Which moisturizer should I use?','2026-07-04 18:51:32');
INSERT INTO "messages" VALUES(24,'session_th7oir1nmok','assistant','Your safety is our top priority. Please stop using the product immediately. If someone ingested the product or is experiencing a severe reaction, contact a healthcare professional or Poison Control right away. Regarding your query: Olay Regenerist Whip Active Moisturizer hydrates skin and reduces wrinkles with a matte finish. It includes Glycerin, Niacinamide (Vitamin B3), and Peptides. Avoid contact with eyes. It is available at CVS, Walgreens, and olay.com. I have flagged this conversation for a human support representative who will follow up with you as soon as possible.','2026-07-04 18:51:32');
INSERT INTO "messages" VALUES(25,'session_or2493fshxj','user','What are the ingredients in Tide Hygienic Clean?','2026-07-05 15:08:03');
INSERT INTO "messages" VALUES(26,'session_or2493fshxj','assistant','Your safety is our top priority. Please stop using the product immediately. If someone ingested the product or is experiencing a severe reaction, contact a healthcare professional or Poison Control right away. Regarding your query: Tide Hygienic Clean Heavy Duty 10X is designed for heavy-duty cleaning and removing grease. It contains Sodium Alcoholethoxy Sulfate and Sodium Borate. Keep out of reach of children. It is available at Walmart and Target. I have flagged this conversation for a human support representative who will follow up with you as soon as possible.','2026-07-05 15:08:03');
INSERT INTO "messages" VALUES(27,'session_2se3fuidj7o','user','Help, my baby swallowed some detergent!','2026-07-05 15:13:27');
INSERT INTO "messages" VALUES(28,'session_2se3fuidj7o','assistant','Your safety is our top priority. Please stop using the product immediately. If someone ingested the product or is experiencing a severe reaction, contact a healthcare professional or Poison Control right away. Regarding your query: Tide Hygienic Clean Heavy Duty 10X is designed for heavy-duty cleaning and removing grease. It contains Sodium Alcoholethoxy Sulfate and Sodium Borate. Keep out of reach of children. It is available at Walmart and Target. I have flagged this conversation for a human support representative who will follow up with you as soon as possible.','2026-07-05 15:13:27');
INSERT INTO "messages" VALUES(29,'session_2se3fuidj7o','user','What are the ingredients in Tide Hygienic Clean?','2026-07-05 15:16:00');
INSERT INTO "messages" VALUES(30,'session_2se3fuidj7o','assistant','Regarding your query: Tide Hygienic Clean Heavy Duty 10X is designed for heavy-duty cleaning and removing grease. It contains Sodium Alcoholethoxy Sulfate and Sodium Borate. Keep out of reach of children. It is available at Walmart and Target.','2026-07-05 15:16:00');
INSERT INTO "messages" VALUES(31,'session_2se3fuidj7o','user','I have sensitive skin. Which moisturizer should I use?','2026-07-05 15:22:52');
INSERT INTO "messages" VALUES(32,'session_2se3fuidj7o','assistant','Your safety is our top priority. Please stop using the product immediately. If someone ingested the product or is experiencing a severe reaction, contact a healthcare professional or Poison Control right away. Regarding your query: Tide Hygienic Clean Heavy Duty 10X is designed for heavy-duty cleaning and removing grease. It contains Sodium Alcoholethoxy Sulfate and Sodium Borate. Keep out of reach of children. It is available at Walmart and Target. I have flagged this conversation for a human support representative who will follow up with you as soon as possible.','2026-07-05 15:22:52');
CREATE TABLE tickets (
                        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        user_message TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        tone TEXT NOT NULL,
                        urgency TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
INSERT INTO "tickets" VALUES(1,'session_1c2d1pfdwwy','hi','Safety Concern','calm','high','2026-07-04 17:24:31');
INSERT INTO "tickets" VALUES(2,'session_th7oir1nmok','I have sensitive skin. Which moisturizer should I use?','Safety Concern','calm','high','2026-07-04 18:51:27');
INSERT INTO "tickets" VALUES(3,'session_2se3fuidj7o','Help, my baby swallowed some detergent!','Safety Concern','calm','high','2026-07-05 15:13:21');
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_tickets_session_id ON tickets(session_id);
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('messages',32);
INSERT INTO "sqlite_sequence" VALUES('tickets',3);
COMMIT;
