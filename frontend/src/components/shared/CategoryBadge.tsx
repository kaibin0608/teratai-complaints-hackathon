import {
  ArrowRightLeft,
  Banknote,
  Copy,
  CreditCard,
  MessageSquare,
  Receipt,
  ShieldAlert,
  type LucideIcon,
} from 'lucide-react'
import { categoryLabel } from '@/lib/labels'
import type { Category } from '@/lib/types'
import { Badge } from './Badge'

const categoryIcon: Record<Category, LucideIcon> = {
  DUPLICATE_CHARGE: Copy,
  FAILED_TRANSFER: ArrowRightLeft,
  ATM_NOT_DISPENSED: Banknote,
  UNAUTHORISED_CARD: CreditCard,
  SCAM_TRANSFER: ShieldAlert,
  FEE_DISPUTE: Receipt,
  SERVICE_QUALITY: MessageSquare,
}

/** Neutral tag: categories help scanning but carry no status colour (Colour System §6). */
export function CategoryBadge({ category }: { category: Category }) {
  return (
    <Badge tone="tag" icon={categoryIcon[category]}>
      {categoryLabel[category]}
    </Badge>
  )
}
