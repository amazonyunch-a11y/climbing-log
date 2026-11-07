import { useEffect, useMemo, useState } from 'react';
import { KeyboardAvoidingView, Modal, Platform, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ActivityIndicator, Button, IconButton, Text } from 'react-native-paper';
import { WebView, type WebViewMessageEvent } from 'react-native-webview';

import { ErrorState } from '@/src/components/ui';
import { colors, layout, spacing } from '@/src/constants/theme';

const KAKAO_WEBVIEW_BASE_URL = 'https://localhost';

export type KakaoPlaceSelection = {
  type: 'KAKAO_PLACE_SELECTED';
  placeName: string;
  roadAddressName: string;
  addressName: string;
  x?: string;
  y?: string;
};

type KakaoSearchPlace = {
  id: string;
  placeName: string;
  roadAddressName: string;
  addressName: string;
  x: string;
  y: string;
};

type KakaoSearchResultsMessage = {
  type: 'KAKAO_SEARCH_RESULTS';
  places: KakaoSearchPlace[];
};

type WebViewStatusMessage = {
  type: 'KAKAO_SDK_READY' | 'KAKAO_SDK_ERROR' | 'KAKAO_MAP_ERROR' | 'KAKAO_NETWORK_ERROR';
  message?: string;
};

type KakaoPlacePickerProps = {
  visible: boolean;
  onDismiss: () => void;
  onSelect: (place: KakaoPlaceSelection) => void;
};

function optionalString(value: unknown) {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined;
}

function parseSearchPlace(value: unknown): KakaoSearchPlace | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const place = value as Record<string, unknown>;
  const id = optionalString(place.id);
  const placeName = optionalString(place.placeName);
  const roadAddressName = optionalString(place.roadAddressName) ?? '';
  const addressName = optionalString(place.addressName) ?? '';
  const x = optionalString(place.x);
  const y = optionalString(place.y);

  if (!id || !placeName || (!roadAddressName && !addressName) || !x || !y) return undefined;
  if (!Number.isFinite(Number(x)) || !Number.isFinite(Number(y))) return undefined;
  return { id, placeName, roadAddressName, addressName, x, y };
}

function parseWebViewMessage(
  data: string,
): KakaoPlaceSelection | KakaoSearchResultsMessage | WebViewStatusMessage | undefined {
  try {
    const parsed: unknown = JSON.parse(data);
    if (!parsed || typeof parsed !== 'object' || !('type' in parsed)) return undefined;

    const message = parsed as Record<string, unknown>;
    if (message.type === 'KAKAO_SDK_READY') return { type: 'KAKAO_SDK_READY' };
    if (
      message.type === 'KAKAO_SDK_ERROR'
      || message.type === 'KAKAO_MAP_ERROR'
      || message.type === 'KAKAO_NETWORK_ERROR'
    ) {
      return { type: message.type, message: optionalString(message.message) };
    }
    if (message.type === 'KAKAO_SEARCH_RESULTS') {
      if (!Array.isArray(message.places)) return undefined;
      const places = message.places.slice(0, 15).map(parseSearchPlace);
      if (places.some((place) => !place)) return undefined;
      return { type: 'KAKAO_SEARCH_RESULTS', places: places as KakaoSearchPlace[] };
    }
    if (message.type !== 'KAKAO_PLACE_SELECTED') return undefined;

    const placeName = optionalString(message.placeName);
    const roadAddressName = optionalString(message.roadAddressName) ?? '';
    const addressName = optionalString(message.addressName) ?? '';
    if (!placeName || (!roadAddressName && !addressName)) return undefined;

    return {
      type: 'KAKAO_PLACE_SELECTED',
      placeName,
      roadAddressName,
      addressName,
      x: optionalString(message.x),
      y: optionalString(message.y),
    };
  } catch {
    return undefined;
  }
}

function createPickerHtml(javascriptKey: string) {
  const sdkUrl = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(javascriptKey)}&libraries=services&autoload=false`;

  return `<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
  <title>카카오 지도 장소 검색</title>
  <style>
    :root { color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #102A43; background: #F4F8FC; }
    * { box-sizing: border-box; }
    html, body, main { width: 100%; height: 100%; }
    body { margin: 0; overflow: hidden; background: #F4F8FC; }
    button, input { font: inherit; }
    main { display: flex; min-height: 0; flex-direction: column; }
    .search-panel { flex: 0 0 auto; padding: 12px 16px 10px; background: #F4F8FC; }
    form { display: flex; gap: 8px; }
    input { flex: 1; min-width: 0; height: 48px; padding: 0 14px; border: 1px solid #CAD8E6; border-radius: 12px; background: #FFFFFF; color: #102A43; font-size: 16px; outline: none; }
    input:focus { border-color: #2474C6; box-shadow: 0 0 0 2px rgba(36, 116, 198, 0.14); }
    .search-button { min-width: 72px; height: 48px; padding: 0 16px; border: 0; border-radius: 12px; background: #0B2447; color: #FFFFFF; font-size: 15px; font-weight: 700; }
    .search-button:disabled { opacity: 0.55; }
    #status { min-height: 20px; margin: 8px 2px 0; color: #5B7087; font-size: 13px; line-height: 18px; }
    #status.error { color: #BA1A1A; }
    .map-shell { position: relative; flex: 0 0 42%; min-height: 220px; max-height: 360px; margin: 0 16px; overflow: hidden; border: 1px solid #CAD8E6; border-radius: 16px; background: #EAF1F8; }
    #map { width: 100%; height: 100%; }
    #map-placeholder { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; padding: 24px; background: #EAF1F8; color: #5B7087; text-align: center; font-size: 14px; line-height: 21px; pointer-events: none; }
    #map-placeholder.hidden { display: none; }
    .results-panel { display: flex; min-height: 0; flex: 1; flex-direction: column; padding: 10px 16px 0; }
    .results-heading { flex: 0 0 auto; margin: 0 2px 8px; color: #0B2447; font-size: 14px; font-weight: 700; }
    #results { min-height: 0; flex: 1; display: grid; align-content: start; gap: 10px; margin: 0; padding: 0 0 24px; overflow-y: auto; list-style: none; -webkit-overflow-scrolling: touch; }
    .empty { padding: 22px 16px; border: 1px dashed #CAD8E6; border-radius: 14px; color: #5B7087; text-align: center; line-height: 21px; }
    .place { width: 100%; padding: 13px 14px; border: 1px solid #CAD8E6; border-radius: 14px; background: #FFFFFF; color: #102A43; text-align: left; cursor: pointer; }
    .place.selected { border: 2px solid #2474C6; padding: 12px 13px; background: #F1F8FF; }
    .place-heading { display: flex; align-items: flex-start; gap: 8px; }
    .place-number { display: inline-flex; width: 24px; height: 24px; flex: 0 0 24px; align-items: center; justify-content: center; border-radius: 12px; background: #DDEEFF; color: #123A66; font-size: 12px; font-weight: 800; }
    .selected .place-number { background: #0B2447; color: #FFFFFF; }
    .place-copy { min-width: 0; flex: 1; }
    .place-name { display: block; overflow-wrap: anywhere; color: #0B2447; font-size: 16px; font-weight: 750; line-height: 22px; }
    .place-address { display: block; margin-top: 5px; overflow-wrap: anywhere; color: #5B7087; font-size: 13px; line-height: 19px; }
    .road-badge { display: inline-block; margin-right: 6px; padding: 1px 5px; border-radius: 5px; background: #E0F5FF; color: #123A66; font-size: 10px; font-weight: 700; vertical-align: 1px; }
    .select-button { display: none; width: 100%; min-height: 44px; margin-top: 12px; border: 0; border-radius: 10px; background: #0B2447; color: #FFFFFF; font-size: 14px; font-weight: 750; }
    .selected .select-button { display: block; }
    @media (max-height: 680px) {
      .search-panel { padding-top: 8px; padding-bottom: 7px; }
      .map-shell { flex-basis: 38%; min-height: 180px; }
      #status { margin-top: 5px; }
    }
  </style>
</head>
<body>
  <main>
    <section class="search-panel">
      <form id="search-form">
        <input id="search-input" type="search" inputmode="search" autocomplete="off" placeholder="암장명 또는 클라이밍 검색" aria-label="장소 검색어" />
        <button class="search-button" id="search-button" type="submit" disabled>검색</button>
      </form>
      <div id="status" role="status" aria-live="polite">카카오 지도를 준비하고 있습니다.</div>
    </section>
    <section class="map-shell" aria-label="장소 검색 지도">
      <div id="map"></div>
      <div id="map-placeholder">지도를 불러오는 중입니다.</div>
    </section>
    <section class="results-panel">
      <div class="results-heading">검색 결과</div>
      <ul id="results"><li class="empty">검색하면 지도와 장소 목록을 함께 확인할 수 있습니다.</li></ul>
    </section>
  </main>
  <script>
    (function () {
      var map;
      var places;
      var ready = false;
      var markers = [];
      var currentPlaces = [];
      var form = document.getElementById('search-form');
      var input = document.getElementById('search-input');
      var searchButton = document.getElementById('search-button');
      var statusElement = document.getElementById('status');
      var resultsElement = document.getElementById('results');
      var mapPlaceholder = document.getElementById('map-placeholder');

      function post(message) {
        if (window.ReactNativeWebView && window.ReactNativeWebView.postMessage) {
          window.ReactNativeWebView.postMessage(JSON.stringify(message));
        }
      }

      function setStatus(message, isError) {
        statusElement.textContent = message;
        statusElement.className = isError ? 'error' : '';
      }

      function setSearching(searching) {
        searchButton.disabled = searching || !ready;
        searchButton.textContent = searching ? '검색 중' : '검색';
      }

      function clearResults(message) {
        while (resultsElement.firstChild) resultsElement.removeChild(resultsElement.firstChild);
        if (message) {
          var empty = document.createElement('li');
          empty.className = 'empty';
          empty.textContent = message;
          resultsElement.appendChild(empty);
        }
      }

      function clearMarkers() {
        markers.forEach(function (marker) { marker.setMap(null); });
        markers = [];
      }

      function markerImage(color) {
        var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="38" height="46" viewBox="0 0 38 46"><path fill="' + color + '" stroke="#FFFFFF" stroke-width="2" d="M19 1C9.6 1 2 8.6 2 18c0 12.7 17 27 17 27s17-14.3 17-27C36 8.6 28.4 1 19 1z"/><circle cx="19" cy="18" r="6" fill="#FFFFFF"/></svg>';
        return new kakao.maps.MarkerImage(
          'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg),
          new kakao.maps.Size(38, 46),
          { offset: new kakao.maps.Point(19, 46) }
        );
      }

      function normalizePlace(place, index) {
        var x = String(place && place.x || '').trim();
        var y = String(place && place.y || '').trim();
        var name = String(place && place.place_name || '').trim();
        var roadAddress = String(place && place.road_address_name || '').trim();
        var address = String(place && place.address_name || '').trim();
        if (!name || (!roadAddress && !address) || !x || !y || !isFinite(Number(x)) || !isFinite(Number(y))) return null;
        return {
          id: String(place.id || (x + ':' + y + ':' + index)),
          placeName: name,
          roadAddressName: roadAddress,
          addressName: address,
          x: x,
          y: y
        };
      }

      function selectPlace(index, shouldScroll) {
        if (index < 0 || index >= currentPlaces.length || !map) return;
        var selected = currentPlaces[index];
        var selectedPosition = new kakao.maps.LatLng(Number(selected.y), Number(selected.x));
        var normalImage = markerImage('#2474C6');
        var selectedImage = markerImage('#0B2447');

        markers.forEach(function (marker, markerIndex) {
          marker.setImage(markerIndex === index ? selectedImage : normalImage);
          marker.setZIndex(markerIndex === index ? 10 : 1);
        });
        Array.prototype.forEach.call(resultsElement.querySelectorAll('.place'), function (card, cardIndex) {
          card.classList.toggle('selected', cardIndex === index);
          card.setAttribute('aria-pressed', cardIndex === index ? 'true' : 'false');
        });
        map.panTo(selectedPosition);
        setStatus('선택한 장소를 확인한 뒤 “이 장소 선택”을 눌러 주세요.', false);
        if (shouldScroll) {
          var selectedCard = resultsElement.querySelectorAll('.place')[index];
          if (selectedCard) selectedCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }

      function confirmPlace(index) {
        var place = currentPlaces[index];
        if (!place) return;
        post({
          type: 'KAKAO_PLACE_SELECTED',
          placeName: place.placeName,
          roadAddressName: place.roadAddressName,
          addressName: place.addressName,
          x: place.x,
          y: place.y
        });
      }

      function renderResults(results) {
        clearMarkers();
        currentPlaces = results.map(normalizePlace).filter(Boolean);
        clearResults();

        if (!currentPlaces.length) {
          setStatus('선택할 수 있는 장소를 찾지 못했습니다.', false);
          clearResults('장소명, 주소와 좌표가 있는 검색 결과가 없습니다.');
          post({ type: 'KAKAO_SEARCH_RESULTS', places: [] });
          return;
        }

        var bounds = new kakao.maps.LatLngBounds();
        var normalImage = markerImage('#2474C6');
        setStatus(currentPlaces.length + '개의 장소를 찾았습니다. 지도나 목록에서 장소를 선택해 주세요.', false);

        currentPlaces.forEach(function (place, index) {
          var position = new kakao.maps.LatLng(Number(place.y), Number(place.x));
          var marker = new kakao.maps.Marker({
            map: map,
            position: position,
            image: normalImage,
            title: place.placeName,
            clickable: true,
            zIndex: 1
          });
          kakao.maps.event.addListener(marker, 'click', function () { selectPlace(index, true); });
          markers.push(marker);
          bounds.extend(position);

          var item = document.createElement('li');
          var card = document.createElement('div');
          var heading = document.createElement('span');
          var number = document.createElement('span');
          var copy = document.createElement('span');
          var name = document.createElement('span');
          var address = document.createElement('span');
          var selectButton = document.createElement('button');

          card.className = 'place';
          card.setAttribute('role', 'button');
          card.setAttribute('tabindex', '0');
          card.setAttribute('aria-pressed', 'false');
          heading.className = 'place-heading';
          number.className = 'place-number';
          number.textContent = String(index + 1);
          copy.className = 'place-copy';
          name.className = 'place-name';
          name.textContent = place.placeName;
          address.className = 'place-address';

          if (place.roadAddressName) {
            var badge = document.createElement('span');
            badge.className = 'road-badge';
            badge.textContent = '도로명';
            address.appendChild(badge);
          }
          address.appendChild(document.createTextNode(place.roadAddressName || place.addressName));
          copy.appendChild(name);
          copy.appendChild(address);
          heading.appendChild(number);
          heading.appendChild(copy);
          card.appendChild(heading);
          card.addEventListener('click', function () { selectPlace(index, false); });
          card.addEventListener('keydown', function (event) {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              selectPlace(index, false);
            }
          });

          selectButton.type = 'button';
          selectButton.className = 'select-button';
          selectButton.textContent = '이 장소 선택';
          selectButton.addEventListener('click', function (event) {
            event.stopPropagation();
            confirmPlace(index);
          });
          card.appendChild(selectButton);
          item.appendChild(card);
          resultsElement.appendChild(item);
        });

        map.relayout();
        if (currentPlaces.length === 1) {
          map.setCenter(new kakao.maps.LatLng(Number(currentPlaces[0].y), Number(currentPlaces[0].x)));
          map.setLevel(3);
        } else {
          map.setBounds(bounds, 52, 52, 52, 52);
        }
        post({ type: 'KAKAO_SEARCH_RESULTS', places: currentPlaces });
      }

      form.addEventListener('submit', function (event) {
        event.preventDefault();
        var keyword = input.value.trim();
        if (!keyword) {
          setStatus('검색어를 입력해 주세요.', true);
          input.focus();
          return;
        }
        if (!ready || !places || !map) {
          setStatus('지도를 준비하고 있습니다. 잠시 후 다시 시도해 주세요.', true);
          return;
        }

        setSearching(true);
        setStatus('장소를 검색하고 있습니다.', false);
        clearMarkers();
        currentPlaces = [];
        clearResults('검색 결과를 불러오는 중입니다.');
        places.keywordSearch(keyword, function (results, searchStatus) {
          setSearching(false);
          if (searchStatus === kakao.maps.services.Status.OK) {
            renderResults(results);
          } else if (searchStatus === kakao.maps.services.Status.ZERO_RESULT) {
            setStatus('검색 결과가 없습니다. 다른 검색어를 입력해 주세요.', false);
            clearResults('검색 결과가 없습니다.');
            post({ type: 'KAKAO_SEARCH_RESULTS', places: [] });
          } else {
            setStatus('장소 검색 중 오류가 발생했습니다. 네트워크를 확인한 뒤 다시 시도해 주세요.', true);
            clearResults('장소 검색에 실패했습니다.');
          }
        }, { size: 15 });
      });

      window.addEventListener('error', function () {
        if (ready) return;
        var message = '카카오 지도 SDK를 초기화하지 못했습니다.';
        setStatus(message, true);
        mapPlaceholder.textContent = message;
        post({ type: 'KAKAO_SDK_ERROR', message: message });
      });

      var sdk = document.createElement('script');
      var sdkTimeout = window.setTimeout(function () {
        if (!ready) {
          var message = '카카오 지도 초기화 시간이 초과되었습니다. JavaScript 키와 등록 도메인을 확인해 주세요.';
          setStatus(message, true);
          mapPlaceholder.textContent = message;
          post({ type: 'KAKAO_SDK_ERROR', message: message });
        }
      }, 12000);
      sdk.src = '${sdkUrl}';
      sdk.async = true;
      sdk.onload = function () {
        if (!window.kakao || !window.kakao.maps || !window.kakao.maps.load) {
          window.clearTimeout(sdkTimeout);
          var message = '카카오 지도 SDK 응답이 올바르지 않습니다.';
          setStatus(message, true);
          mapPlaceholder.textContent = message;
          post({ type: 'KAKAO_SDK_ERROR', message: message });
          return;
        }
        kakao.maps.load(function () {
          try {
            if (!kakao.maps.services || !kakao.maps.services.Places) throw new Error('services unavailable');
            map = new kakao.maps.Map(document.getElementById('map'), {
              center: new kakao.maps.LatLng(37.5665, 126.9780),
              level: 8
            });
            map.addControl(new kakao.maps.ZoomControl(), kakao.maps.ControlPosition.RIGHT);
            places = new kakao.maps.services.Places();
            ready = true;
            window.clearTimeout(sdkTimeout);
            mapPlaceholder.className = 'hidden';
            setSearching(false);
            setStatus('암장명이나 “클라이밍”을 검색해 보세요.', false);
            window.setTimeout(function () { map.relayout(); }, 0);
            post({ type: 'KAKAO_SDK_READY' });
          } catch (error) {
            window.clearTimeout(sdkTimeout);
            var message = '카카오 지도를 초기화하지 못했습니다. 키와 도메인 설정을 확인해 주세요.';
            setStatus(message, true);
            mapPlaceholder.textContent = message;
            post({ type: 'KAKAO_MAP_ERROR', message: message });
          }
        });
      };
      sdk.onerror = function () {
        window.clearTimeout(sdkTimeout);
        var message = '카카오 지도 SDK를 불러오지 못했습니다. 네트워크 연결을 확인해 주세요.';
        setStatus(message, true);
        mapPlaceholder.textContent = message;
        post({ type: 'KAKAO_NETWORK_ERROR', message: message });
      };
      document.head.appendChild(sdk);
    })();
  </script>
</body>
</html>`;
}

export function KakaoPlacePicker({ visible, onDismiss, onSelect }: KakaoPlacePickerProps) {
  const insets = useSafeAreaInsets();
  const javascriptKey = process.env.EXPO_PUBLIC_KAKAO_JAVASCRIPT_KEY?.trim() ?? '';
  const [webViewError, setWebViewError] = useState<string>();
  const [isLoading, setIsLoading] = useState(true);
  const [resultCount, setResultCount] = useState<number>();
  const [reloadKey, setReloadKey] = useState(0);
  const html = useMemo(() => createPickerHtml(javascriptKey), [javascriptKey]);

  useEffect(() => {
    if (!visible) return;
    setWebViewError(undefined);
    setIsLoading(true);
    setResultCount(undefined);
    setReloadKey((current) => current + 1);
  }, [visible]);

  const handleMessage = (event: WebViewMessageEvent) => {
    const message = parseWebViewMessage(event.nativeEvent.data);
    if (!message) return;

    if (message.type === 'KAKAO_PLACE_SELECTED') {
      onSelect(message);
      onDismiss();
      return;
    }
    if (message.type === 'KAKAO_SEARCH_RESULTS') {
      setResultCount(message.places.length);
      return;
    }
    if (
      message.type === 'KAKAO_SDK_ERROR'
      || message.type === 'KAKAO_MAP_ERROR'
      || message.type === 'KAKAO_NETWORK_ERROR'
    ) {
      setIsLoading(false);
      setWebViewError(message.message ?? '카카오 지도를 초기화하지 못했습니다.');
      return;
    }
    setIsLoading(false);
  };

  const retry = () => {
    setWebViewError(undefined);
    setIsLoading(true);
    setResultCount(undefined);
    setReloadKey((current) => current + 1);
  };

  const missingKey = !javascriptKey;
  const subtitle = resultCount === undefined
    ? '장소를 선택하면 등록 폼에 자동 입력됩니다.'
    : `${resultCount}개의 검색 결과`;

  return <Modal
    visible={visible}
    animationType="slide"
    presentationStyle="fullScreen"
    statusBarTranslucent
    navigationBarTranslucent
    onRequestClose={onDismiss}
  >
    <KeyboardAvoidingView
      style={[styles.modalRoot, { paddingTop: insets.top, paddingBottom: insets.bottom }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.header}>
        <IconButton icon="arrow-left" accessibilityLabel="암장 등록 화면으로 돌아가기" onPress={onDismiss} />
        <View style={styles.titleGroup}>
          <Text variant="titleLarge" style={styles.title} numberOfLines={1}>지도에서 암장 찾기</Text>
          <Text variant="bodySmall" style={styles.subtitle} numberOfLines={1}>{subtitle}</Text>
        </View>
        <IconButton icon="close" accessibilityLabel="장소 검색 닫기" onPress={onDismiss} />
      </View>

      {missingKey ? <View style={styles.stateContainer}>
        <ErrorState message="카카오 JavaScript 키가 설정되지 않았습니다. frontend/.env에 EXPO_PUBLIC_KAKAO_JAVASCRIPT_KEY를 설정한 뒤 Expo를 다시 시작해 주세요." />
        <Button mode="outlined" onPress={onDismiss} contentStyle={styles.buttonContent}>닫기</Button>
      </View> : webViewError ? <View style={styles.stateContainer}>
        <ErrorState message={webViewError} onRetry={retry} />
        <Button mode="outlined" onPress={onDismiss} contentStyle={styles.buttonContent}>취소</Button>
      </View> : <View style={styles.webViewContainer}>
        <WebView
          key={reloadKey}
          source={{ html, baseUrl: KAKAO_WEBVIEW_BASE_URL }}
          originWhitelist={['https://*']}
          javaScriptEnabled
          domStorageEnabled
          mixedContentMode="never"
          javaScriptCanOpenWindowsAutomatically={false}
          setSupportMultipleWindows={false}
          keyboardDisplayRequiresUserAction={false}
          onMessage={handleMessage}
          onLoadStart={() => setIsLoading(true)}
          onError={({ nativeEvent }) => {
            setIsLoading(false);
            setWebViewError(nativeEvent.description || '장소 검색 화면을 불러오지 못했습니다.');
          }}
          onHttpError={({ nativeEvent }) => {
            setIsLoading(false);
            setWebViewError(`장소 검색 화면을 불러오지 못했습니다. (HTTP ${nativeEvent.statusCode})`);
          }}
          style={styles.webView}
        />
        {isLoading && <View pointerEvents="none" style={styles.loadingOverlay}>
          <ActivityIndicator size="large" />
          <Text variant="bodyMedium" style={styles.subtitle}>카카오 지도를 불러오는 중입니다.</Text>
        </View>}
      </View>}
    </KeyboardAvoidingView>
  </Modal>;
}

const styles = StyleSheet.create({
  modalRoot: { flex: 1, backgroundColor: colors.background },
  header: { minHeight: 68, flexDirection: 'row', alignItems: 'center', gap: spacing.xs, paddingHorizontal: spacing.xs, paddingVertical: spacing.xs, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, backgroundColor: colors.surface },
  titleGroup: { flex: 1, minWidth: 0, gap: 2 },
  title: { color: colors.navy900, fontWeight: '700' },
  subtitle: { color: colors.textMuted },
  webViewContainer: { flex: 1 },
  webView: { flex: 1, backgroundColor: colors.background },
  loadingOverlay: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, alignItems: 'center', justifyContent: 'center', gap: spacing.md, backgroundColor: colors.background },
  stateContainer: { flex: 1, justifyContent: 'center', gap: spacing.lg, padding: layout.screenPadding },
  buttonContent: { minHeight: layout.minTouchTarget },
});
