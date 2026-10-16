import * as ImagePicker from 'expo-image-picker';
import { useEvent } from 'expo';
import { VideoView, useVideoPlayer } from 'expo-video';
import { useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { Platform, ScrollView, StyleSheet, View } from 'react-native';
import { ActivityIndicator, Button, Card, IconButton, Snackbar, Text } from 'react-native-paper';

import { videosApi } from '@/src/api/videos';
import { ApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { ConfirmDialog, EmptyState, SectionHeader, uiStyles } from '@/src/components/ui';
import { colors, radius, spacing } from '@/src/constants/theme';
import type { SessionVideo } from '@/src/types/video';
import { uploadSessionVideo, validateVideoAsset } from '@/src/utils/videoStorage';
import { formatKstDateTime } from '@/src/utils/date';

const MAX_VIDEOS_PER_SESSION = 5;

function VideoPreview({ video }: { video: SessionVideo }) {
  const player = useVideoPlayer(video.file_url, (instance) => {
    instance.loop = false;
  });
  const status = useEvent(player, 'statusChange', { status: player.status });
  return <View style={styles.preview}>
    <VideoView player={player} style={styles.video} nativeControls contentFit="contain" />
    {status.status === 'error' && <Text style={styles.playbackError}>영상을 재생하지 못했습니다. 네트워크 또는 public URL 설정을 확인해 주세요.</Text>}
  </View>;
}

export function SessionVideoSection({ sessionId }: { sessionId: number }) {
  const { user } = useAuth();
  const [videos, setVideos] = useState<SessionVideo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ current: number; total: number }>();
  const [deletingId, setDeletingId] = useState<number>();
  const [deleteTarget, setDeleteTarget] = useState<SessionVideo>();
  const [error, setError] = useState<string>();
  const [successMessage, setSuccessMessage] = useState<string>();
  const requestId = useRef(0);

  const load = useCallback(async () => {
    const currentRequestId = ++requestId.current;
    setIsLoading(true);
    try {
      const result = await videosApi.list(sessionId);
      if (currentRequestId === requestId.current) setVideos(result);
    } catch (cause) {
      if (currentRequestId === requestId.current) setError(cause instanceof ApiError ? cause.message : '영상 목록을 불러오지 못했습니다.');
    } finally {
      if (currentRequestId === requestId.current) setIsLoading(false);
    }
  }, [sessionId]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  const supportsMultipleSelection = Platform.OS !== 'ios' || Number.parseInt(String(Platform.Version), 10) >= 14;
  const remainingVideoSlots = Math.max(0, MAX_VIDEOS_PER_SESSION - videos.length);
  const isAtVideoLimit = remainingVideoSlots === 0;

  const pickAndUpload = async () => {
    if (!user) { setError('로그인 사용자 정보를 찾을 수 없습니다.'); return; }
    if (isAtVideoLimit) { setError('세션당 영상은 최대 5개까지 등록할 수 있습니다.'); return; }
    setError(undefined);
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Videos,
      allowsMultipleSelection: supportsMultipleSelection,
      selectionLimit: supportsMultipleSelection ? 0 : 1,
      quality: 1,
    });
    if (result.canceled || result.assets.length === 0) return;

    const uploadAssets = result.assets.slice(0, remainingVideoSlots);
    const excludedCount = result.assets.length - uploadAssets.length;

    const failedUploads: string[] = [];
    let successfulUploads = 0;
    try {
      setIsUploading(true);
      setUploadProgress({ current: 0, total: uploadAssets.length });
      for (const [index, asset] of uploadAssets.entries()) {
        setUploadProgress({ current: index + 1, total: uploadAssets.length });
        try {
          validateVideoAsset(asset);
          const storagePath = await uploadSessionVideo(asset, user.id, sessionId);
          try {
            await videosApi.create(sessionId, { storage_path: storagePath });
          } catch (cause) {
            if (cause instanceof ApiError && cause.status === 409) {
              throw new Error('세션당 영상은 최대 5개까지 등록할 수 있습니다.');
            }
            throw new Error(`Storage 업로드 후 기록 등록에 실패했습니다. Storage 파일은 남아 있을 수 있습니다. ${cause instanceof ApiError ? cause.message : ''}`.trim());
          }
          successfulUploads += 1;
        } catch (cause) {
          failedUploads.push(`${index + 1}번: ${cause instanceof Error ? cause.message : '업로드 실패'}`);
        }
      }
      await load();
      if (successfulUploads > 0) setSuccessMessage(`${successfulUploads}개 영상 업로드를 완료했습니다.${excludedCount ? ` 최대 5개 제한으로 ${excludedCount}개는 제외했습니다.` : ''}${failedUploads.length ? ` ${failedUploads.length}개는 실패했습니다.` : ''}`);
      else if (excludedCount) setError(`세션당 영상은 최대 5개까지 등록할 수 있습니다. ${excludedCount}개 파일은 업로드하지 않았습니다.`);
      if (failedUploads.length) setError(`영상 업로드 결과: ${failedUploads.join(' / ')}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '영상 업로드에 실패했습니다.');
    } finally {
      setIsUploading(false);
      setUploadProgress(undefined);
    }
  };

  const remove = async (videoId: number) => {
    setDeletingId(videoId);
    setError(undefined);
    try {
      await videosApi.remove(videoId);
      setDeleteTarget(undefined);
      await load();
      setSuccessMessage('영상 파일과 기록이 삭제되었습니다.');
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : '영상 파일과 기록을 삭제하지 못했습니다. 다시 시도해 주세요.');
    } finally {
      setDeletingId(undefined);
    }
  };

  return <Card mode="outlined" style={uiStyles.card}>
    <Card.Content style={styles.content}>
      <SectionHeader title="영상" description={`최대 5개 · 현재 ${videos.length}개`} action={<Button mode="contained-tonal" icon="video-plus-outline" compact onPress={() => void pickAndUpload()} loading={isUploading} disabled={isUploading || Boolean(deletingId) || isAtVideoLimit}>추가</Button>} />
      {isAtVideoLimit && <Text variant="bodySmall" style={styles.limitNotice}>세션당 영상은 최대 5개까지 등록할 수 있습니다.</Text>}
      {!supportsMultipleSelection && <Text variant="bodySmall" style={styles.notice}>이 기기에서는 한 번에 여러 영상 선택이 지원되지 않습니다.</Text>}
      {isUploading && <View style={styles.uploading}><ActivityIndicator /><Text>영상 업로드 중입니다. ({uploadProgress?.current ?? 0}/{uploadProgress?.total ?? 0})</Text></View>}
      {isLoading ? <View style={styles.loading}><ActivityIndicator /></View> : videos.length === 0 ? <EmptyState title="등록된 영상이 없어요" description="등반 영상을 추가해 세션과 함께 보관하세요." icon="video-outline" /> : <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.list} snapToInterval={260} decelerationRate="fast">
        {videos.map((video, index) => <Card key={video.id} mode="outlined" style={styles.item}>
          <Card.Content style={styles.itemContent}>
            <View style={styles.itemHeader}><Text variant="titleSmall" style={styles.itemTitle}>영상 {index + 1}</Text><IconButton icon="delete-outline" iconColor={colors.error} onPress={() => setDeleteTarget(video)} disabled={isUploading || Boolean(deletingId)} loading={deletingId === video.id} accessibilityLabel={`영상 ${index + 1} 삭제`} /></View>
            <VideoPreview video={video} />
            <Text variant="bodySmall" style={styles.notice}>업로드 {formatKstDateTime(video.uploaded_at)}</Text>
          </Card.Content>
        </Card>)}
      </ScrollView>}
    </Card.Content>
    <ConfirmDialog visible={Boolean(deleteTarget)} title="영상 삭제" message="영상 파일과 기록을 함께 삭제할까요? 삭제한 파일은 복구할 수 없습니다." busy={Boolean(deletingId)} onCancel={() => setDeleteTarget(undefined)} onConfirm={() => deleteTarget && void remove(deleteTarget.id)} />
    <Snackbar visible={Boolean(successMessage)} onDismiss={() => setSuccessMessage(undefined)} duration={2500}>{successMessage}</Snackbar>
    <Snackbar visible={Boolean(error)} onDismiss={() => setError(undefined)}>{error}</Snackbar>
  </Card>;
}

const styles = StyleSheet.create({
  content: { gap: spacing.md },
  uploading: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, padding: spacing.md, borderRadius: radius.md, backgroundColor: colors.sky100 },
  loading: { minHeight: 80, justifyContent: 'center', alignItems: 'center' },
  notice: { color: colors.textMuted }, limitNotice: { color: colors.warning, backgroundColor: '#FFF1D6', padding: spacing.sm, borderRadius: radius.sm },
  list: { gap: spacing.md, paddingVertical: spacing.xs, paddingRight: spacing.md },
  item: { width: 248 },
  itemContent: { gap: spacing.sm, padding: spacing.md }, itemHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', minHeight: 40 }, itemTitle: { color: colors.navy900, fontWeight: '700' }, preview: { gap: spacing.sm },
  video: { width: '100%', height: 140, borderRadius: radius.md, backgroundColor: colors.navy950 },
  playbackError: { color: colors.error },
});
