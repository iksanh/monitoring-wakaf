// JavaScript vanilla seperlunya: menu samping, konfirmasi hapus, draft offline.
(function () {
  var tombol = document.getElementById('tombol-menu');
  var samping = document.getElementById('samping');
  if (tombol && samping) {
    tombol.addEventListener('click', function () { samping.classList.toggle('buka'); });
    document.addEventListener('click', function (e) {
      if (window.innerWidth >= 900) return;
      if (!samping.contains(e.target) && e.target !== tombol) samping.classList.remove('buka');
    });
  }

  // Halaman masuk: tombol lihat sandi + peringatan Caps Lock.
  var sandi = document.getElementById('sandi');
  var lihat = document.getElementById('tombol-lihat-sandi');
  if (sandi && lihat) {
    lihat.addEventListener('click', function () {
      var terbuka = sandi.type === 'text';
      sandi.type = terbuka ? 'password' : 'text';
      lihat.textContent = terbuka ? 'Lihat' : 'Sembunyi';
      lihat.setAttribute('aria-pressed', terbuka ? 'false' : 'true');
      sandi.focus();
    });
  }
  var petunjukCaps = document.getElementById('petunjuk-capslock');
  if (sandi && petunjukCaps) {
    var periksaCaps = function (e) {
      if (typeof e.getModifierState !== 'function') return;
      petunjukCaps.hidden = !e.getModifierState('CapsLock');
    };
    sandi.addEventListener('keydown', periksaCaps);
    sandi.addEventListener('keyup', periksaCaps);
    sandi.addEventListener('blur', function () { petunjukCaps.hidden = true; });
  }

  document.querySelectorAll('[data-konfirmasi]').forEach(function (el) {
    el.addEventListener('submit', function (e) {
      if (!window.confirm(el.dataset.konfirmasi)) e.preventDefault();
    });
  });

  // Dropdown desa mengikuti kecamatan terpilih.
  document.querySelectorAll('select[data-induk-kecamatan]').forEach(function (sel) {
    var induk = document.getElementById(sel.dataset.indukKecamatan);
    if (!induk) return;
    function saring() {
      var kec = induk.value;
      var adaTerpilih = false;
      Array.prototype.forEach.call(sel.options, function (o) {
        var cocok = !o.value || !kec || o.dataset.kecamatan === kec;
        o.hidden = !cocok;
        o.disabled = !cocok;
        if (cocok && o.selected) adaTerpilih = true;
      });
      if (!adaTerpilih) sel.value = '';
    }
    induk.addEventListener('change', saring);
    saring();
  });

  // Draft offline: simpan isian form ke localStorage, pulihkan kalau koneksi putus.
  document.querySelectorAll('form[data-draft]').forEach(function (form) {
    var kunci = 'draft:' + form.dataset.draft;
    var simpan = function () {
      var data = {};
      new FormData(form).forEach(function (v, k) { if (typeof v === 'string') data[k] = v; });
      try { localStorage.setItem(kunci, JSON.stringify(data)); } catch (e) {}
    };
    try {
      var tersimpan = JSON.parse(localStorage.getItem(kunci) || 'null');
      if (tersimpan && form.dataset.draftPulih !== 'tidak') {
        Object.keys(tersimpan).forEach(function (k) {
          var el = form.elements[k];
          if (el && !el.value) el.value = tersimpan[k];
        });
      }
    } catch (e) {}
    form.addEventListener('input', simpan);
    form.addEventListener('submit', function () {
      try { localStorage.removeItem(kunci); } catch (e) {}
    });
  });

  // Ambil koordinat dari GPS perangkat (form objek wakaf & form kunjungan).
  document.querySelectorAll('[data-ambil-koordinat]').forEach(function (tombol) {
    var form = tombol.closest('form');
    if (!form) return;
    var status = form.querySelector('[data-koordinat-status]');
    var labelAsli = tombol.textContent;

    function kabar(teks) {
      if (status) status.textContent = teks;
      else tombol.textContent = teks;
    }

    tombol.addEventListener('click', function () {
      if (!navigator.geolocation) {
        kabar('Perangkat ini tidak punya fitur lokasi.');
        return;
      }
      // Chrome & Safari memblokir geolocation di luar HTTPS/localhost, tanpa
      // memunculkan dialog izin sama sekali.
      if (!window.isSecureContext) {
        kabar('Lokasi diblokir browser karena halaman ini bukan HTTPS. '
              + 'Isi manual dulu, atau buka aplikasi lewat alamat https.');
        return;
      }

      tombol.disabled = true;
      tombol.textContent = 'Mengambil…';
      kabar('Mencari sinyal GPS, mohon tunggu…');

      navigator.geolocation.getCurrentPosition(function (pos) {
        form.elements['latitude'].value = pos.coords.latitude.toFixed(6);
        form.elements['longitude'].value = pos.coords.longitude.toFixed(6);
        // Isi tautan peta kalau tersedia di form ini dan masih kosong.
        var peta = form.elements['url_maps'];
        if (peta && !peta.value) {
          peta.value = 'https://www.google.com/maps?q='
            + pos.coords.latitude.toFixed(6) + ',' + pos.coords.longitude.toFixed(6);
        }
        tombol.disabled = false;
        tombol.textContent = 'Ambil Ulang';
        var akurasi = Math.round(pos.coords.accuracy || 0);
        kabar('Koordinat terisi. Perkiraan ketelitian ±' + akurasi + ' m'
              + (akurasi > 50 ? ' — agak kasar, coba ambil ulang di tempat terbuka.' : '.'));
      }, function (galat) {
        tombol.disabled = false;
        tombol.textContent = labelAsli;
        if (galat.code === galat.PERMISSION_DENIED) {
          kabar('Izin lokasi ditolak. Aktifkan lewat ikon gembok di bilah alamat.');
        } else if (galat.code === galat.POSITION_UNAVAILABLE) {
          kabar('Sinyal GPS tidak didapat. Coba keluar ruangan lalu ulangi.');
        } else {
          kabar('Waktu habis sebelum GPS terkunci. Coba lagi.');
        }
      }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 });
    });
  });
})();
