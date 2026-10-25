SELECT
  DATE(date) AS day,
  ANY_VALUE(lang) AS lang,
  FARM_FINGERPRINT(url) AS url_hash,
  ANY_VALUE(score) AS score,
  ARRAY_AGG(STRUCT(
    REPLACE(REGEXP_REPLACE(ent.wikipediaUrl, r'^https?://[^/]+/wiki/', ''), ' ', '_') AS wiki,
    ent.mid AS mid
  )) AS entities
FROM `gdelt-bq.gdeltv2.geg_gcnlapi`,
UNNEST(entities) AS ent
WHERE date >= TIMESTAMP('2016-11-14')
  AND date < TIMESTAMP('2016-12-12')
  AND lang = 'en'
  AND (
    REPLACE(REGEXP_REPLACE(ent.wikipediaUrl, r'^https?://[^/]+/wiki/', ''), ' ', '_') IN ('Adobe_Inc.', 'Amazon.com', 'Amazon_(company)', 'Amgen', 'Android_(operating_system)', 'Apple_Inc.', 'Chevron_Corporation', 'Chipotle_Mexican_Grill', 'Clorox', 'Colgate-Palmolive', 'Converse_(brand)', 'Darden_Restaurants', 'Dell', 'Dish_Network', 'Duke_Energy', 'Eli_Lilly_and_Company', 'Elon_Musk', 'Ford_Motor_Company', 'General_Mills', 'General_Motors', 'Google', 'Hewlett-Packard', 'Hurley_International', 'IBM', 'IPhone', 'John_Deere', 'Kellanova', 'Kimberly-Clark', 'Larry_Page_and_Sundar_Pichai', 'Logitech', 'Lowe\'s', 'MacBook', 'Marathon_Petroleum', 'Mastercard', 'Meta_Platforms', 'Microsoft', 'Microsoft_Azure', 'Microsoft_Windows', 'NextEra_Energy', 'Nike,_Inc.', 'Nio_Inc.', 'Oracle_Corporation', 'Salesforce', 'Samsung_Electronics', 'Satya_Nadella', 'Snap_Inc.', 'Snapchat', 'Southern_Company', 'T-Mobile_US', 'Tesla,_Inc.', 'Tesla_Model_3', 'Tesla_Model_S', 'The_Hershey_Company', 'The_New_York_Times_Company', 'Tim_Cook', 'Toyota', 'Umbro', 'Valero_Energy', 'Vertex_Pharmaceuticals', 'YouTube', 'iPhone')
    OR ent.mid IN ('/m/01nn79', '/m/01sgwn', '/m/027lnzs', '/m/02wxtgw', '/m/03mnk', '/m/045c7b', '/m/04cylkl', '/m/04r_8', '/m/04y7lrx', '/m/05njw', '/m/09jcvs', '/m/0k8z', '/m/0mgkg', '/m/0py9b')
  )
GROUP BY day, url_hash
