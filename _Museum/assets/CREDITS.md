# Asset credits (Chronicle Museum)

All third-party textures are **CC0 1.0 (public domain)**; no attribution is required, but we credit the sources anyway.
Downloaded 2026-09-28 with the user's approval. The viewer loads the raw maps straight from `textures/<set>/`
(`albedo.jpg`, `normal.jpg` (OpenGL +Y), `roughness.jpg` / `metalness.jpg`, or Poly Haven's packed `arm.jpg` =
AO / roughness / metalness) and tiles them in world space (`web/js/matlib.js`).

| Set | Source | Asset | Maps kept | Licence |
|---|---|---|---|---|
| parquet | Poly Haven | [herringbone_parquet](https://polyhaven.com/a/herringbone_parquet) (2K) | diffuse, normal (GL), ARM | CC0 ([polyhaven.com/license](https://polyhaven.com/license)) |
| marble | ambientCG | [Marble012](https://ambientcg.com/view?id=Marble012) (2K) | color, normal (GL), roughness | CC0 ([docs.ambientcg.com/license](https://docs.ambientcg.com/license/)) |
| plaster | ambientCG | [PaintedPlaster017](https://ambientcg.com/view?id=PaintedPlaster017) (1K) | color, normal (GL), roughness | CC0 |
| metal | ambientCG | [Metal048A](https://ambientcg.com/view?id=Metal048A) (1K) | color, normal (GL), roughness, metalness | CC0 |

`texture_downloads.json` / `texture_map.json` record how the sets were fetched (the v2 Blender pack they describe is retired).
Paintings and portraits: see the per-work credits in `data/museum-manifest.json` (Wikimedia Commons / the Earth Chronicle site).

## Sky

`sky.jpg` is the scene background (equirectangular, sRGB; `web/js/render.js`), seen through the rotunda oculus and
wherever a view leaves the building: [Kloofendal 48d Partly Cloudy (Pure Sky)](https://polyhaven.com/a/kloofendal_48d_partly_cloudy_puresky)
by Greg Zaal (sky edits Jarod Guest), Poly Haven, CC0 ([polyhaven.com/license](https://polyhaven.com/license)); the
tonemapped JPG downscaled to 2048 × 1024.

## Models

Third-party 3D models placed in the museum (fetched by `_Museum/fetch_models.py` from `assets/models.json`).

| id | title | maker / date | museum / source | licence | file |
|---|---|---|---|---|---|
| `ph-bench` | [Painted wooden bench](https://polyhaven.com/a/painted_wooden_bench) | Poly Haven | Poly Haven | CC0 | `painted_wooden_bench_1k.gltf` (1943 KB) |
| `ph-brass-vase` | [Brass vase](https://polyhaven.com/a/brass_vase_01) | Poly Haven | Poly Haven | CC0 | `brass_vase_01_1k.gltf` (822 KB) |
| `ph-bull-head` | [Bull head](https://polyhaven.com/a/bull_head) | Poly Haven (photoscan) | Poly Haven | CC0 | `bull_head_1k.gltf` (1973 KB) |
| `ph-ceramic-vase` | [Antique ceramic vase](https://polyhaven.com/a/antique_ceramic_vase_01) | Poly Haven | Poly Haven | CC0 | `antique_ceramic_vase_01_1k.gltf` (513 KB) |
| `ph-chandelier-01` | [Chandelier](https://polyhaven.com/a/Chandelier_01) | Poly Haven | Poly Haven | CC0 | `Chandelier_01_1k.gltf` (1275 KB) |
| `ph-chandelier-02` | [Chandelier](https://polyhaven.com/a/Chandelier_02) | Poly Haven | Poly Haven | CC0 | `Chandelier_02_1k.gltf` (1154 KB) |
| `ph-gothic-statue` | [Gothic statue](https://polyhaven.com/a/gothic_statue) | Poly Haven (photoscan) | Poly Haven | CC0 | `gothic_statue_1k.gltf` (3885 KB) |
| `ph-horse-head` | [Horse head](https://polyhaven.com/a/horse_head) | Poly Haven (photoscan) | Poly Haven | CC0 | `horse_head_1k.gltf` (1723 KB) |
| `ph-lantern-chandelier` | [Lantern chandelier](https://polyhaven.com/a/lantern_chandelier_01) | Poly Haven | Poly Haven | CC0 | `lantern_chandelier_01_1k.gltf` (1445 KB) |
| `ph-marble-bust` | [Marble bust](https://polyhaven.com/a/marble_bust_01) | Poly Haven (photoscan) | Poly Haven | CC0 | `marble_bust_01_1k.gltf` (877 KB) |
| `ph-ornate-mirror` | [Ornate mirror](https://polyhaven.com/a/ornate_mirror_01) | Poly Haven | Poly Haven | CC0 | `ornate_mirror_01_1k.gltf` (661 KB) |
| `si-cosmic-buddha` | [Buddha draped in robes portraying the Realms of Desire (the Cosmic Buddha)](https://3d.si.edu/object/3d/cosmic-buddha:d8c62be8-4ebc-11ea-b77f-2e728ce88125) | Northern Qi dynasty, China · 550–577 | National Museum of Asian Art (Freer Gallery) | CC0 | `model.glb` (885 KB) |
| `si-dying-tecumseh` | [The Dying Tecumseh](https://3d.si.edu/object/3d/dying-tecumseh:a572abe8-d60a-4ad5-aa86-6609e85ec4a6) | Ferdinand Pettrich · 1856 | Smithsonian American Art Museum | CC0 | `model.glb` (879 KB) |
| `si-fangyi` | [Ritual wine container (fangyi) with masks, serpents and birds](https://3d.si.edu/object/3d/ritual-wine-container-fangyi:d8c62f94-4ebc-11ea-b77f-2e728ce88125) | Shang dynasty, China · ca. 1100 BCE | National Museum of Asian Art (Freer Gallery) | CC0 | `model.glb` (221 KB) |
| `si-garfield` | [James Garfield](https://3d.si.edu/object/3d/james-garfield:d2887438-0f09-4e72-887d-0966ff177149) | John Quincy Adams Ward · c. 1883–87 | National Portrait Gallery | CC0 | `model.glb` (147 KB) |
| `si-gathering-of-buddhas` | [Gathering of Buddhas and bodhisattvas](https://3d.si.edu/object/3d/gathering-buddhas-and-bodhisattvas:476ad7f6-6add-448d-af7f-9f2ca9ba9cb6) | Northern Qi dynasty, China · 550–577 | National Museum of Asian Art (Freer Gallery) | CC0 | `model.glb` (1039 KB) |
| `si-girl-skating` | [Girl Skating](https://3d.si.edu/object/3d/girl-skating:e8d1f790-28a8-492d-84f5-cf2817f8cdcf) | Abastenia St. Leger Eberle · 1906 | Smithsonian American Art Museum | CC0 | `model.glb` (131 KB) |
| `si-gong-ewer` | [Ritual wine ewer (gong) with masks, dragons and real animals](https://3d.si.edu/object/3d/ritual-wine-ewer-gong:d8c646aa-4ebc-11ea-b77f-2e728ce88125) | Shang dynasty, China · ca. 1100–1050 BCE | National Museum of Asian Art (Freer Gallery) | CC0 | `model.glb` (198 KB) |
| `si-greek-slave` | [Model of the Greek Slave](https://3d.si.edu/object/3d/model-greek-slave:8edffe56-c358-4c3a-a61f-019f615ccef0) | Hiram Powers · 1843 | Smithsonian American Art Museum | CC0 | `model.glb` (834 KB) |
| `si-greenough-washington` | [George Washington](https://3d.si.edu/object/3d/george-washington:789cf90a-4387-4ac1-9e96-c7d6a7b9d26f) | Horatio Greenough · 1840 | Smithsonian American Art Museum | CC0 | `model.glb` (978 KB) |
| `si-helen-keller` | [Helen Adams Keller](https://3d.si.edu/object/3d/helen-keller:d8c64ccc-4ebc-11ea-b77f-2e728ce88125) | Onorio Ruotolo · 1916 | National Portrait Gallery | CC0 | `model.glb` (96 KB) |
| `si-houdon-washington` | [George Washington](https://3d.si.edu/object/3d/george-washington-houdon:ff28cb3a-ad00-43b3-a928-fa61ab0a288f) | Jean-Antoine Houdon · c. 1786 | National Portrait Gallery | CC0 | `model.glb` (159 KB) |
| `si-jackson-mills` | [Andrew Jackson](https://3d.si.edu/object/3d/andrew-jackson-mills:80a9e13c-8e58-4b74-8482-63fd5ee197d8) | Clark Mills · 1855 | National Portrait Gallery | CC0 | `model.glb` (175 KB) |
| `si-kangxi-baluster-vase` | [Baluster vase from a five-piece garniture](https://3d.si.edu/object/3d/baluster-vase:d8c6393a-4ebc-11ea-b77f-2e728ce88125) | Kangxi reign, Qing dynasty, China · 1662–1722 | National Museum of Asian Art (Freer Gallery) | CC0 | `model.glb` (117 KB) |
| `si-kangxi-beaker-vase` | [Beaker-shaped vase from a five-piece garniture](https://3d.si.edu/object/3d/beaker-shaped-vase:d8c63a70-4ebc-11ea-b77f-2e728ce88125) | Kangxi reign, Qing dynasty, China · 1662–1722 | National Museum of Asian Art (Freer Gallery) | CC0 | `model.glb` (111 KB) |
| `si-kongo-tusk` | [Carved tusk](https://3d.si.edu/object/3d/tusk:c3a1b002-84cd-462f-841d-109dc4aeea36) | Kongo artist, Loango coast · ca. 1860 | National Museum of African Art | CC0 | `model.glb` (193 KB) |
| `si-lincoln-mills-mask` | [Abraham Lincoln (life mask)](https://3d.si.edu/object/3d/abraham-lincoln-mills:c02c239d-5ebf-4a7a-a368-e2288bbf4b31) | Clark Mills · 1865 | National Portrait Gallery | CC0 | `model.glb` (153 KB) |
| `si-old-arrow-maker` | [Old Arrow Maker](https://3d.si.edu/object/3d/old-arrow-maker:082c87e9-1fe0-4772-b4c6-fe6d59bd6e74) | Edmonia Lewis · 1872 | Smithsonian American Art Museum | CC0 | `model.glb` (158 KB) |
| `si-ravenna-washington` | [George Washington](https://3d.si.edu/object/3d/george-washington-ravenna:d8c63fde-4ebc-11ea-b77f-2e728ce88125) | Massimiliano Ravenna, after Giuseppe Ceracchi · c. 1819 | National Portrait Gallery | CC0 | `model.glb` (119 KB) |
| `si-roosevelt-relief` | [Theodore Roosevelt](https://3d.si.edu/object/3d/theodore-roosevelt-farnham:1788235b-d2bc-4287-8fb5-f2965a069fd9) | Sally James Farnham · 1906 | National Portrait Gallery | CC0 | `model.glb` (136 KB) |
| `si-temne-horn` | [Hunting horn](https://3d.si.edu/object/3d/hunting-horn:ad94884b-fdd7-4fc3-a692-e53b787d78e6) | Temne artist, Sierra Leone · late 15th century | National Museum of African Art | CC0 | `model.glb` (161 KB) |
| `si-waterston-bust` | [Helen Ruthven Waterston](https://3d.si.edu/object/3d/helen-ruthven-waterston:d825c526-69dd-472a-8d47-7da7fbe88fb7) | Edmonia Lewis · 1862 | Smithsonian American Art Museum | CC0 | `model.glb` (134 KB) |
| `si-western-paradise` | [Western Paradise of the Buddha Amitabha](https://3d.si.edu/object/3d/western-paradise-buddha-amitabha:727b4bb6-ce87-40de-b07d-d492c1404221) | Northern Qi dynasty, China · 550–577 | National Museum of Asian Art (Freer Gallery) | CC0 | `model.glb` (1040 KB) |
| `si-winged-monster` | [Kneeling winged monster](https://3d.si.edu/object/3d/kneeling-winged-monster:0dc68216-3651-44c7-99cf-18e5d4d1eb9f) | Northern Qi dynasty, China · 550–577 | National Museum of Asian Art (Freer Gallery) | CC0 | `model.glb` (157 KB) |
| `si-wounded-scout` | [The Wounded Scout, a Friend in the Swamp](https://3d.si.edu/object/3d/wounded-scout-friend-swamp:a09bb967-a8b8-46a2-9322-37b25a452b46) | John Rogers · 1864 | Smithsonian American Art Museum | CC0 | `model.glb` (173 KB) |
| `si-xianglu` | [Lidded incense burner (xianglu) with geometric decoration and narrative scenes](https://3d.si.edu/object/3d/lidded-incense-burner-xianglu:ce850625-2cf1-4c6f-9086-0d5845d9a664) | Western Han dynasty, China · ca. 2nd century BCE | National Museum of Asian Art (Freer Gallery) | CC0 | `model.glb` (129 KB) |

Smithsonian models are CC0 releases of the Smithsonian Open Access programme (3d.si.edu); Poly Haven assets are CC0 (polyhaven.com). Local drop-ins (Scan the World, CC BY-NC 4.0) carry their own credit line.
