import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import config
from api.routes_project import router as project_router

app = FastAPI(
    title="Full Auto Story Animation Studio",
    description="Tam Otomatik Hikâyeli 2D Animasyon Video Oluşturma Platformu (0 TL Maliyet)",
    version="1.0.0-stage8",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(project_router)

app.mount("/exports", StaticFiles(directory=str(config.EXPORTS_DIR)), name="exports")
app.mount("/css", StaticFiles(directory=str(config.FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(config.FRONTEND_DIR / "js")), name="js")

@app.get("/")
async def serve_mobile_studio():
    index_file = config.FRONTEND_DIR / "index.html"
    return FileResponse(
        str(index_file),
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```eof

### 2. `frontend/index.html`
```html:frontend/index.html
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
    <title>Full Auto Story Animation Studio</title>
    <link rel="stylesheet" href="/css/styles.css" />
</head>
<body>
    <div class="app-shell">
        <header class="top-bar">
            <div class="brand">
                <div class="brand-icon">🎬</div>
                <div>
                    <h1 class="brand-title">STORY STUDIO</h1>
                    <p class="brand-subtitle">Tam Otomatik 2D Animasyon • 9:16</p>
                </div>
            </div>
            <div id="server-status-badge" class="status-badge checking">
                <span class="dot"></span>
                <span id="server-status-text">Bağlanıyor...</span>
            </div>
        </header>

        <main id="screen-create" class="screen active">
            <section class="card">
                <div class="card-header">
                    <span class="step-pill">1</span>
                    <h2>Proje Oluştur</h2>
                </div>

                <div class="form-group">
                    <label for="project-name">Proje / Bölüm Adı</label>
                    <input type="text" id="project-name" class="text-input" placeholder="Örn: Karanlık İstasyon - Bölüm 1" maxlength="80" autocomplete="off" />
                </div>

                <div class="form-group">
                    <label>Hikâye Türü ve Atmosfer</label>
                    <div id="genre-grid" class="genre-grid">
                        <button type="button" class="genre-chip selected" data-genre="horror"><span>🕯️</span> Korku & Gerilim</button>
                        <button type="button" class="genre-chip" data-genre="zombie"><span>🧟</span> Zombi & Salgın</button>
                        <button type="button" class="genre-chip" data-genre="survival"><span>🔦</span> Hayatta Kalma</button>
                        <button type="button" class="genre-chip" data-genre="mystery"><span>🕵️</span> Gizem</button>
                        <button type="button" class="genre-chip" data-genre="scifi"><span>🛸</span> Bilim Kurgu</button>
                        <button type="button" class="genre-chip" data-genre="adventure"><span>🧭</span> Macera</button>
                    </div>
                </div>

                <div class="form-group">
                    <label for="previous-choice">Önceki Bölüm İzleyici Seçimi (İsteğe Bağlı)</label>
                    <select id="previous-choice" class="select-input">
                        <option value="">İlk Bölüm (Bağımsız Hikâye)</option>
                        <option value="A">Önceki Bölümde A Şıkkı Seçildi</option>
                        <option value="B">Önceki Bölümde B Şıkkı Seçildi</option>
                        <option value="C">Önceki Bölümde C Şıkkı Seçildi</option>
                    </select>
                </div>
            </section>

            <section class="card">
                <div class="card-header">
                    <span class="step-pill">2</span>
                    <div>
                        <h2>Anlatıcı Sesi (Zorunlu)</h2>
                        <p class="card-desc">iPhone Dosyalar veya Sesli Notlar uygulamasından MP3, WAV, M4A anlatıcı sesinizi yükleyin.</p>
                    </div>
                </div>

                <input type="file" id="narrator-file-input" accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg" class="hidden-file-input" />

                <div id="narrator-empty-state" class="upload-dropzone">
                    <div class="upload-icon">🎙️</div>
                    <p class="upload-title">Anlatıcı Ses Dosyasını Seç</p>
                    <p class="upload-hint">MP3, WAV, M4A (iPhone Sesli Notlar) desteklenir</p>
                    <button type="button" id="btn-pick-narrator" class="btn btn-secondary">Dosya Seç</button>
                </div>

                <div id="narrator-loaded-state" class="file-loaded-card hidden">
                    <div class="file-info-row">
                        <div class="file-badge">🎙️ Anlatıcı</div>
                        <span id="narrator-file-size" class="file-size">0 MB</span>
                    </div>
                    <p id="narrator-file-name" class="file-name">anlatici.mp3</p>
                    <audio id="narrator-audio-preview" controls preload="metadata" class="audio-player"></audio>
                    <div class="file-actions">
                        <button type="button" id="btn-change-narrator" class="btn btn-small btn-outline">Değiştir</button>
                        <button type="button" id="btn-remove-narrator" class="btn btn-small btn-danger">Sil</button>
                    </div>
                </div>
            </section>

            <section class="card">
                <div class="card-header">
                    <span class="step-pill">3</span>
                    <div>
                        <h2>Karakter Konuşma Sesleri</h2>
                        <p class="card-desc">Varsa karakterlerin seslerini ayrı ayrı ekleyin.</p>
                    </div>
                </div>

                <div id="character-list-container" class="character-list"></div>
                <button type="button" id="btn-add-character" class="btn btn-dashed">+ Karakter Sesi Ekle</button>
            </section>

            <div id="form-error-box" class="alert-box error hidden"></div>

            <div class="sticky-bottom-bar">
                <button type="button" id="btn-start-create" class="btn btn-primary btn-large">✨ Videoyu Otomatik Oluştur</button>
            </div>
        </main>

        <main id="screen-progress" class="screen">
            <section class="card progress-card">
                <div class="spinner-ring"><span id="progress-percent-text">0%</span></div>
                <h2 id="progress-project-title" class="progress-title">Proje Hazırlanıyor</h2>
                <p id="progress-current-label" class="progress-subtitle">Ses dosyaları yükleniyor...</p>

                <div class="progress-bar-track">
                    <div id="progress-bar-fill" class="progress-bar-fill" style="width: 0%;"></div>
                </div>

                <div id="ambiguity-modal-card" class="card hidden" style="text-align:left; border-color:#f59e0b; margin-bottom:16px;">
                    <h3 style="font-size:15px; color:#fcd34d; margin-bottom:6px;">⚠️ Karakter Eşleştirmesini Doğrula</h3>
                    <p class="card-desc" style="margin-bottom:12px;">Sistem aşağıdaki karakter seslerinin kime ait olduğunu doğrulamanızı istiyor:</p>
                    <div id="ambiguity-items-list" class="character-list"></div>
                    <button type="button" id="btn-confirm-mappings" class="btn btn-primary btn-large" style="margin-top:8px;">✓ Eşleştirmeyi Onayla ve Devam Et</button>
                </div>

                <ul class="stage-checklist">
                    <li id="step-item-1" class="stage-item active"><span class="stage-indicator">1</span><div class="stage-text"><strong>Ses Analizi ve Sahne Planı</strong><small>Mekân, kamera, 2D aksiyon ve SFX çıkarılıyor</small></div></li>
                    <li id="step-item-2" class="stage-item"><span class="stage-indicator">2</span><div class="stage-text"><strong>Karakterler Hazırlanıyor</strong><small>Tutarlı 2D rig ve 1080x1920 mekânlar çiziliyor</small></div></li>
                    <li id="step-item-3" class="stage-item"><span class="stage-indicator">3</span><div class="stage-text"><strong>Animasyonlar Oluşturuluyor</strong><small>Lip-sync ve hareketler işleniyor</small></div></li>
                    <li id="step-item-4" class="stage-item"><span class="stage-indicator">4</span><div class="stage-text"><strong>Ses Efektleri Ekleniyor</strong><small>Orijinal sesler, SFX ve müzik dengeleniyor</small></div></li>
                    <li id="step-item-5" class="stage-item"><span class="stage-indicator">5</span><div class="stage-text"><strong>Video Render Ediliyor</strong><small>1080x1920 MP4 çıktı hazırlanıyor</small></div></li>
                </ul>
            </section>
        </main>

        <main id="screen-result" class="screen">
            <section class="card">
                <div class="result-header">
                    <span class="success-badge">✓ 2D Animasyon ve Master Ses Hazır</span>
                    <h2 id="result-project-title">Hikâye Videosu Hazır</h2>
                    <p id="result-meta-info" class="card-desc">1080x1920 • 9:16 Dikey • 30 FPS MP4</p>
                </div>

                <div class="video-frame-9x16">
                    <video id="result-video-player" controls playsinline webkit-playsinline preload="metadata" class="video-element hidden"></video>
                    <img id="result-keyframe-image" alt="Sahne Önizleme" class="video-element hidden" />
                    <div id="video-placeholder-notice" class="video-placeholder">
                        <div class="placeholder-icon">🎬</div>
                        <h3>Aşama 8 MP4 Video Hazır!</h3>
                        <p id="placeholder-status-msg" style="font-size:12px; color:#cbd5e1; margin-top:6px;">Tam otomatik 2D animasyon videosu oluşturuldu.</p>
                    </div>
                </div>

                <div id="master-audio-box" class="file-loaded-card hidden" style="margin-bottom: 16px;">
                    <div class="file-info-row">
                        <span class="file-badge">🔊 Master Ses (Orijinal Ses + SFX + Müzik)</span>
                    </div>
                    <audio id="result-master-audio" controls preload="metadata" class="audio-player" style="margin-top:6px; margin-bottom:0;"></audio>
                </div>

                <div class="interactive-choices-box" style="margin-bottom: 16px;">
                    <h3 style="font-size: 14px; margin-bottom: 8px;">🎭 Tutarlı 2D Karakter Rig Kadrosu</h3>
                    <div id="result-characters-list" style="display:grid; grid-template-columns: repeat(2, 1fr); gap:10px;"></div>
                </div>

                <div class="interactive-choices-box" style="margin-bottom: 16px;">
                    <h3 style="font-size: 14px; margin-bottom: 8px;">📋 Otomatik Üretilen Sahne & Kamera Planı</h3>
                    <div id="result-scenes-list" class="choices-list"></div>
                </div>

                <div class="interactive-choices-box">
                    <h3 style="font-size: 14px; margin-bottom: 8px;">🔀 Bölüm Sonu İzleyici Seçenekleri (A/B/C)</h3>
                    <div id="result-choices-list" class="choices-list"></div>
                </div>

                <div class="result-actions" style="margin-top:16px; display:flex; flex-direction:column; gap:10px;">
                    <button type="button" id="btn-export-mp4" class="btn btn-primary btn-large">⬇️ MP4 Olarak Dışa Aktar</button>
                    <button type="button" id="btn-new-project" class="btn btn-secondary btn-large">🔄 Yeni Proje Oluştur</button>
                </div>
            </section>
        </main>
    </div>

    <script src="/js/app.js"></script>
</body>
</html>
```eof

