import type { ReactElement, ReactNode } from 'react';
import { RefreshControlProps, ScrollView, StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ActivityIndicator, Button, Card, Dialog, Icon, Portal, Text, useTheme } from 'react-native-paper';

import { colors, layout, radius, spacing } from '@/src/constants/theme';

type ScreenProps = { children: ReactNode; scroll?: boolean; contentStyle?: StyleProp<ViewStyle>; keyboardShouldPersistTaps?: 'always' | 'never' | 'handled'; refreshControl?: ReactElement<RefreshControlProps> };

export function Screen({ children, scroll = false, contentStyle, keyboardShouldPersistTaps = 'handled', refreshControl }: ScreenProps) {
  const content = [styles.content, contentStyle];
  return <SafeAreaView style={styles.safeArea} edges={['top', 'left', 'right']}>
    {scroll ? <ScrollView contentContainerStyle={content} keyboardShouldPersistTaps={keyboardShouldPersistTaps} refreshControl={refreshControl}>{children}</ScrollView> : <View style={content}>{children}</View>}
  </SafeAreaView>;
}

export function PageHeader({ title, subtitle, onBack, action }: { title: string; subtitle?: string; onBack?: () => void; action?: ReactNode }) {
  return <View style={styles.pageHeader}>
    {onBack && <Button icon="arrow-left" mode="text" compact onPress={onBack} accessibilityLabel="이전 화면" style={styles.backButton}>이전</Button>}
    <View style={styles.pageTitleGroup}><Text variant="headlineMedium" style={styles.pageTitle} numberOfLines={2}>{title}</Text>{subtitle && <Text variant="bodyMedium" style={styles.muted}>{subtitle}</Text>}</View>
    {action}
  </View>;
}

export function SectionHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return <View style={styles.sectionHeader}><View style={styles.sectionTitleGroup}><Text variant="titleLarge" style={styles.sectionTitle}>{title}</Text>{description && <Text variant="bodySmall" style={styles.muted}>{description}</Text>}</View>{action}</View>;
}

export function LoadingState({ label = '불러오는 중입니다.' }: { label?: string }) {
  return <View style={styles.state}><ActivityIndicator size="large" /><Text style={styles.muted}>{label}</Text></View>;
}

export function EmptyState({ title, description, icon = 'inbox-outline', action }: { title: string; description?: string; icon?: string; action?: ReactNode }) {
  const theme = useTheme();
  return <Card mode="outlined" style={styles.stateCard}><Card.Content style={styles.state}><View style={styles.stateIcon}><Icon source={icon} size={28} color={theme.colors.primary} /></View><Text variant="titleMedium" style={styles.stateTitle}>{title}</Text>{description && <Text variant="bodyMedium" style={[styles.muted, styles.stateDescription]}>{description}</Text>}{action}</Card.Content></Card>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <Card mode="outlined" style={styles.errorCard}><Card.Content style={styles.errorContent}><Icon source="alert-circle-outline" size={24} color={colors.error} /><View style={styles.errorText}><Text variant="titleSmall" style={{ color: colors.error }}>문제가 발생했습니다</Text><Text variant="bodyMedium">{message}</Text></View>{onRetry && <Button mode="outlined" onPress={onRetry}>다시 시도</Button>}</Card.Content></Card>;
}

export function ConfirmDialog({ visible, title, message, confirmLabel = '삭제', busy = false, onCancel, onConfirm }: { visible: boolean; title: string; message: string; confirmLabel?: string; busy?: boolean; onCancel: () => void; onConfirm: () => void }) {
  return <Portal><Dialog visible={visible} onDismiss={busy ? undefined : onCancel}><Dialog.Icon icon="alert-outline" /><Dialog.Title>{title}</Dialog.Title><Dialog.Content><Text variant="bodyMedium">{message}</Text></Dialog.Content><Dialog.Actions><Button onPress={onCancel} disabled={busy}>취소</Button><Button textColor={colors.error} onPress={onConfirm} loading={busy} disabled={busy}>{confirmLabel}</Button></Dialog.Actions></Dialog></Portal>;
}

export const uiStyles = StyleSheet.create({
  card: { borderColor: colors.border, backgroundColor: colors.surface },
  cardContent: { gap: spacing.md },
  primaryButton: { minHeight: layout.minTouchTarget, justifyContent: 'center' },
  input: { backgroundColor: colors.surface },
  muted: { color: colors.textMuted },
  destructiveButton: { borderColor: colors.error },
});

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  content: { flexGrow: 1, width: '100%', maxWidth: layout.contentMaxWidth, alignSelf: 'center', paddingHorizontal: layout.screenPadding, paddingTop: spacing.md, paddingBottom: spacing.xxxl, gap: layout.sectionGap },
  pageHeader: { minHeight: 56, flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  backButton: { marginLeft: -spacing.md },
  pageTitleGroup: { flex: 1, gap: spacing.xs },
  pageTitle: { color: colors.navy950, fontWeight: '800', letterSpacing: -0.4 },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.md },
  sectionTitleGroup: { flex: 1, gap: 2 },
  sectionTitle: { color: colors.navy900, fontWeight: '700' },
  muted: { color: colors.textMuted },
  stateCard: { borderColor: colors.border, backgroundColor: colors.surface },
  state: { minHeight: 148, alignItems: 'center', justifyContent: 'center', gap: spacing.sm, padding: spacing.xl },
  stateIcon: { width: 52, height: 52, borderRadius: radius.pill, backgroundColor: colors.sky100, alignItems: 'center', justifyContent: 'center' },
  stateTitle: { color: colors.navy900, fontWeight: '700', textAlign: 'center' },
  stateDescription: { textAlign: 'center', maxWidth: 300 },
  errorCard: { borderColor: '#F2B8B5', backgroundColor: colors.errorContainer },
  errorContent: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  errorText: { flex: 1, gap: 2 },
});
