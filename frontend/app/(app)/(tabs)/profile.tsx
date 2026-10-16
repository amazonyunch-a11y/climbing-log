import { useAuth } from '@/src/auth/AuthProvider';
import { LoadingState, PageHeader, Screen, uiStyles } from '@/src/components/ui';
import { colors, radius, spacing } from '@/src/constants/theme';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Avatar, Button, Card, Divider, Icon, Text } from 'react-native-paper';

export default function ProfileScreen() {
  const { user, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const onLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
    }
  };

  if (!user) return <Screen><LoadingState label="프로필을 불러오는 중입니다." /></Screen>;

  return <Screen scroll>
    <PageHeader title="프로필" subtitle="계정 정보를 확인하고 로그인 상태를 관리하세요." />
    <Card mode="outlined" style={[uiStyles.card, styles.profileCard]}><Card.Content style={styles.cardContent}>
      <Avatar.Text size={72} label={(user.nickname || 'U').slice(0, 1).toUpperCase()} style={styles.avatar} labelStyle={styles.avatarLabel} />
      <View style={styles.identity}><Text variant="headlineSmall" style={styles.nickname}>{user.nickname}</Text><Text variant="bodyMedium" style={uiStyles.muted}>{user.email}</Text></View>
      <Divider />
      <View style={styles.infoRow}><View style={styles.infoIcon}><Icon source="account-outline" size={21} color={colors.blue600} /></View><View style={styles.infoText}><Text variant="labelMedium" style={uiStyles.muted}>닉네임</Text><Text variant="bodyLarge">{user.nickname}</Text></View></View>
      <View style={styles.infoRow}><View style={styles.infoIcon}><Icon source="email-outline" size={21} color={colors.blue600} /></View><View style={styles.infoText}><Text variant="labelMedium" style={uiStyles.muted}>이메일</Text><Text variant="bodyLarge" numberOfLines={2}>{user.email}</Text></View></View>
    </Card.Content></Card>
    <Card mode="outlined" style={uiStyles.card}><Card.Content style={styles.notice}><Icon source="information-outline" size={22} color={colors.blue600} /><Text variant="bodyMedium" style={styles.noticeText}>현재 MVP에서는 프로필 정보를 조회할 수 있으며, 수정 기능은 제공하지 않습니다.</Text></Card.Content></Card>
    <Button mode="outlined" icon="logout" textColor={colors.error} style={uiStyles.destructiveButton} onPress={onLogout} loading={isLoggingOut} disabled={isLoggingOut} contentStyle={uiStyles.primaryButton}>로그아웃</Button>
  </Screen>;
}

const styles = StyleSheet.create({
  profileCard: { borderRadius: radius.lg }, cardContent: { gap: spacing.lg, paddingVertical: spacing.lg }, avatar: { alignSelf: 'center', backgroundColor: colors.navy900 }, avatarLabel: { color: '#FFFFFF', fontWeight: '800' }, identity: { alignItems: 'center', gap: spacing.xs }, nickname: { color: colors.navy900, fontWeight: '800' },
  infoRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md }, infoIcon: { width: 42, height: 42, borderRadius: radius.md, backgroundColor: colors.sky100, alignItems: 'center', justifyContent: 'center' }, infoText: { flex: 1, gap: 2 },
  notice: { flexDirection: 'row', alignItems: 'center', gap: spacing.md }, noticeText: { flex: 1, color: colors.textMuted },
});
