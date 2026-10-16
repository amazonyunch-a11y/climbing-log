import { EmptyState, PageHeader, Screen } from '@/src/components/ui';

type PlaceholderScreenProps = {
  title: string;
  description: string;
};

export function PlaceholderScreen({ title, description }: PlaceholderScreenProps) {
  return <Screen><PageHeader title={title} /><EmptyState title="준비 중인 화면입니다" description={description} icon="hammer-wrench" /></Screen>;
}
