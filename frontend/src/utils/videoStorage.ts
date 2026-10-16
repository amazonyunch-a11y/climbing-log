import type { ImagePickerAsset } from 'expo-image-picker';

import { storageBucket, supabase } from '@/src/api/supabase';

const MAX_VIDEO_SIZE_BYTES = 50 * 1024 * 1024;
const extensionToMimeType = {
  mp4: 'video/mp4',
  mov: 'video/quicktime',
  m4v: 'video/x-m4v',
} as const;

type VideoExtension = keyof typeof extensionToMimeType;

function getExtension(asset: ImagePickerAsset): VideoExtension {
  const filename = (asset.fileName ?? asset.uri).split('?')[0];
  const extension = filename.split('.').pop()?.toLowerCase();
  if (!extension || !(extension in extensionToMimeType)) {
    throw new Error('mp4, mov, m4v 형식의 영상만 업로드할 수 있습니다.');
  }
  return extension as VideoExtension;
}

function createUuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (character) => {
    const random = Math.floor(Math.random() * 16);
    const value = character === 'x' ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}

export function validateVideoAsset(asset: ImagePickerAsset): { extension: VideoExtension; contentType: string } {
  const extension = getExtension(asset);
  const inferredContentType = extensionToMimeType[extension];
  if (asset.mimeType && asset.mimeType !== inferredContentType) {
    throw new Error('선택한 파일의 확장자와 MIME type이 일치하지 않습니다.');
  }
  if (asset.fileSize !== undefined && asset.fileSize > MAX_VIDEO_SIZE_BYTES) {
    throw new Error('50MB 이하의 영상만 업로드할 수 있습니다.');
  }
  return { extension, contentType: asset.mimeType ?? inferredContentType };
}

export async function uploadSessionVideo(asset: ImagePickerAsset, userId: number, sessionId: number): Promise<string> {
  if (!supabase || !storageBucket) {
    throw new Error('Supabase Storage 환경변수가 설정되지 않았습니다.');
  }
  const { extension, contentType } = validateVideoAsset(asset);
  const fileResponse = await fetch(asset.uri);
  if (!fileResponse.ok) throw new Error('선택한 영상 파일을 읽지 못했습니다.');
  const fileData = await fileResponse.arrayBuffer();
  if (fileData.byteLength > MAX_VIDEO_SIZE_BYTES) {
    throw new Error('50MB 이하의 영상만 업로드할 수 있습니다.');
  }

  const storagePath = `videos/user-${userId}/session-${sessionId}/${createUuid()}.${extension}`;
  const { error } = await supabase.storage.from(storageBucket).upload(storagePath, fileData, {
    contentType,
    upsert: false,
  });
  if (error) throw new Error(`Storage 업로드에 실패했습니다: ${error.message}`);
  return storagePath;
}
