import { HandHeart } from 'lucide-react'
import { Badge } from './Badge'

/** Customer aged 65+ on received_at (Colour System §6: vulnerable customer tag). */
export function VulnerableBadge() {
  return (
    <Badge tone="aubergine" icon={HandHeart} title="Customer aged 65 or over on the received date">
      Vulnerable 65+
    </Badge>
  )
}
