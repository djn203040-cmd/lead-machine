export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      jobs: {
        Row: {
          attempts: number
          created_at: string
          error: string | null
          finished_at: string | null
          id: string
          lead_id: string | null
          payload: Json
          result: Json | null
          search_id: string | null
          started_at: string | null
          status: string
          type: string
        }
        Insert: {
          attempts?: number
          created_at?: string
          error?: string | null
          finished_at?: string | null
          id?: string
          lead_id?: string | null
          payload?: Json
          result?: Json | null
          search_id?: string | null
          started_at?: string | null
          status?: string
          type: string
        }
        Update: {
          attempts?: number
          created_at?: string
          error?: string | null
          finished_at?: string | null
          id?: string
          lead_id?: string | null
          payload?: Json
          result?: Json | null
          search_id?: string | null
          started_at?: string | null
          status?: string
          type?: string
        }
        Relationships: [
          {
            foreignKeyName: "jobs_lead_id_fkey"
            columns: ["lead_id"]
            isOneToOne: false
            referencedRelation: "leads"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "jobs_search_id_fkey"
            columns: ["search_id"]
            isOneToOne: false
            referencedRelation: "searches"
            referencedColumns: ["id"]
          },
        ]
      }
      lead_angles: {
        Row: {
          angle_da: string | null
          competitor_angle_type: string | null
          competitor_name: string | null
          cta_da: string | null
          generated_at: string
          lead_id: string
          objections: Json
          opening_line_da: string | null
          summary_da: string | null
          weaknesses_da: string | null
        }
        Insert: {
          angle_da?: string | null
          competitor_angle_type?: string | null
          competitor_name?: string | null
          cta_da?: string | null
          generated_at?: string
          lead_id: string
          objections?: Json
          opening_line_da?: string | null
          summary_da?: string | null
          weaknesses_da?: string | null
        }
        Update: {
          angle_da?: string | null
          competitor_angle_type?: string | null
          competitor_name?: string | null
          cta_da?: string | null
          generated_at?: string
          lead_id?: string
          objections?: Json
          opening_line_da?: string | null
          summary_da?: string | null
          weaknesses_da?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "lead_angles_lead_id_fkey"
            columns: ["lead_id"]
            isOneToOne: true
            referencedRelation: "leads"
            referencedColumns: ["id"]
          },
        ]
      }
      lead_calls: {
        Row: {
          called_at: string
          id: string
          lead_id: string
          outcome: string
          user_id: string | null
        }
        Insert: {
          called_at?: string
          id?: string
          lead_id: string
          outcome: string
          user_id?: string | null
        }
        Update: {
          called_at?: string
          id?: string
          lead_id?: string
          outcome?: string
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "lead_calls_lead_id_fkey"
            columns: ["lead_id"]
            isOneToOne: false
            referencedRelation: "leads"
            referencedColumns: ["id"]
          },
        ]
      }
      lead_enrichment: {
        Row: {
          contact: Json
          cvr: Json
          financial: Json
          last_enriched_at: string | null
          lead_id: string
          social: Json
          website: Json
        }
        Insert: {
          contact?: Json
          cvr?: Json
          financial?: Json
          last_enriched_at?: string | null
          lead_id: string
          social?: Json
          website?: Json
        }
        Update: {
          contact?: Json
          cvr?: Json
          financial?: Json
          last_enriched_at?: string | null
          lead_id?: string
          social?: Json
          website?: Json
        }
        Relationships: [
          {
            foreignKeyName: "lead_enrichment_lead_id_fkey"
            columns: ["lead_id"]
            isOneToOne: true
            referencedRelation: "leads"
            referencedColumns: ["id"]
          },
        ]
      }
      lead_followups: {
        Row: {
          created_at: string
          follow_up_date: string
          id: string
          lead_id: string
          reminder_sent: boolean
          user_id: string | null
        }
        Insert: {
          created_at?: string
          follow_up_date: string
          id?: string
          lead_id: string
          reminder_sent?: boolean
          user_id?: string | null
        }
        Update: {
          created_at?: string
          follow_up_date?: string
          id?: string
          lead_id?: string
          reminder_sent?: boolean
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "lead_followups_lead_id_fkey"
            columns: ["lead_id"]
            isOneToOne: false
            referencedRelation: "leads"
            referencedColumns: ["id"]
          },
        ]
      }
      lead_mail: {
        Row: {
          address_line: string | null
          arm: string
          batch_id: string | null
          city: string | null
          company_name: string
          country: string
          created_at: string
          created_by: string | null
          first_name: string | null
          first_scanned_at: string | null
          focus_text: string | null
          followup_id: string | null
          id: string
          is_seed: boolean
          landing_headline: string | null
          landing_video_url: string | null
          last_scanned_at: string | null
          lead_id: string
          letter_chars: number | null
          letter_text: string | null
          observation_approved_at: string | null
          observation_approved_by: string | null
          observation_text: string | null
          opted_out_at: string | null
          postal_code: string | null
          recipient_name: string | null
          reject_reason: string | null
          scan_count: number
          slug: string
          status: string
          updated_at: string
        }
        Insert: {
          address_line?: string | null
          arm: string
          batch_id?: string | null
          city?: string | null
          company_name: string
          country?: string
          created_at?: string
          created_by?: string | null
          first_name?: string | null
          first_scanned_at?: string | null
          focus_text?: string | null
          followup_id?: string | null
          id?: string
          is_seed?: boolean
          landing_headline?: string | null
          landing_video_url?: string | null
          last_scanned_at?: string | null
          lead_id: string
          letter_chars?: number | null
          letter_text?: string | null
          observation_approved_at?: string | null
          observation_approved_by?: string | null
          observation_text?: string | null
          opted_out_at?: string | null
          postal_code?: string | null
          recipient_name?: string | null
          reject_reason?: string | null
          scan_count?: number
          slug: string
          status?: string
          updated_at?: string
        }
        Update: {
          address_line?: string | null
          arm?: string
          batch_id?: string | null
          city?: string | null
          company_name?: string
          country?: string
          created_at?: string
          created_by?: string | null
          first_name?: string | null
          first_scanned_at?: string | null
          focus_text?: string | null
          followup_id?: string | null
          id?: string
          is_seed?: boolean
          landing_headline?: string | null
          landing_video_url?: string | null
          last_scanned_at?: string | null
          lead_id?: string
          letter_chars?: number | null
          letter_text?: string | null
          observation_approved_at?: string | null
          observation_approved_by?: string | null
          observation_text?: string | null
          opted_out_at?: string | null
          postal_code?: string | null
          recipient_name?: string | null
          reject_reason?: string | null
          scan_count?: number
          slug?: string
          status?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "lead_mail_batch_id_fkey"
            columns: ["batch_id"]
            isOneToOne: false
            referencedRelation: "mail_batches"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "lead_mail_lead_id_fkey"
            columns: ["lead_id"]
            isOneToOne: false
            referencedRelation: "leads"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "lead_mail_followup_id_fkey"
            columns: ["followup_id"]
            isOneToOne: false
            referencedRelation: "lead_followups"
            referencedColumns: ["id"]
          },
        ]
      }
      lead_notes: {
        Row: {
          body: string
          created_at: string
          id: string
          lead_id: string
          updated_at: string
          user_id: string | null
        }
        Insert: {
          body: string
          created_at?: string
          id?: string
          lead_id: string
          updated_at?: string
          user_id?: string | null
        }
        Update: {
          body?: string
          created_at?: string
          id?: string
          lead_id?: string
          updated_at?: string
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "lead_notes_lead_id_fkey"
            columns: ["lead_id"]
            isOneToOne: false
            referencedRelation: "leads"
            referencedColumns: ["id"]
          },
        ]
      }
      lead_scores: {
        Row: {
          breakdown: Json
          lead_id: string
          scored_at: string
          total: number
        }
        Insert: {
          breakdown?: Json
          lead_id: string
          scored_at?: string
          total: number
        }
        Update: {
          breakdown?: Json
          lead_id?: string
          scored_at?: string
          total?: number
        }
        Relationships: [
          {
            foreignKeyName: "lead_scores_lead_id_fkey"
            columns: ["lead_id"]
            isOneToOne: true
            referencedRelation: "leads"
            referencedColumns: ["id"]
          },
        ]
      }
      leads: {
        Row: {
          address: string | null
          assigned_to: string | null
          branche_text: string | null
          branchekode: string | null
          city: string | null
          company_form: string | null
          company_name: string
          created_at: string
          cvr_number: string | null
          cvr_status: string | null
          dial_priority: number
          discovered_url: string | null
          email: string | null
          employees_band: string | null
          employees_exact: number | null
          enrichment_status: string
          founded_at: string | null
          has_phone: boolean
          id: string
          is_archived: boolean
          is_sole_trader: boolean
          kommune: string | null
          phone: string[]
          phone_type: string | null
          pipeline_status: string
          pm_lead_id: string | null
          pm_synced_at: string | null
          postal_code: string | null
          reklamebeskyttet: boolean
          robinson_screened_at: string | null
          score: number | null
          search_id: string | null
          suppressed: boolean
          suppression_reason: string | null
          updated_at: string
          website: string | null
          website_need: string
          website_quality: string | null
          website_source: string | null
        }
        Insert: {
          address?: string | null
          assigned_to?: string | null
          branche_text?: string | null
          branchekode?: string | null
          city?: string | null
          company_form?: string | null
          company_name: string
          created_at?: string
          cvr_number?: string | null
          cvr_status?: string | null
          dial_priority?: number
          discovered_url?: string | null
          email?: string | null
          employees_band?: string | null
          employees_exact?: number | null
          enrichment_status?: string
          founded_at?: string | null
          id?: string
          is_archived?: boolean
          is_sole_trader?: boolean
          kommune?: string | null
          phone?: string[]
          pipeline_status?: string
          pm_lead_id?: string | null
          pm_synced_at?: string | null
          postal_code?: string | null
          reklamebeskyttet?: boolean
          robinson_screened_at?: string | null
          score?: number | null
          search_id?: string | null
          suppressed?: boolean
          suppression_reason?: string | null
          updated_at?: string
          website?: string | null
          website_need?: string
          website_quality?: string | null
          website_source?: string | null
        }
        Update: {
          address?: string | null
          assigned_to?: string | null
          branche_text?: string | null
          branchekode?: string | null
          city?: string | null
          company_form?: string | null
          company_name?: string
          created_at?: string
          cvr_number?: string | null
          cvr_status?: string | null
          dial_priority?: number
          discovered_url?: string | null
          email?: string | null
          employees_band?: string | null
          employees_exact?: number | null
          enrichment_status?: string
          founded_at?: string | null
          id?: string
          is_archived?: boolean
          is_sole_trader?: boolean
          kommune?: string | null
          phone?: string[]
          pipeline_status?: string
          pm_lead_id?: string | null
          pm_synced_at?: string | null
          postal_code?: string | null
          reklamebeskyttet?: boolean
          robinson_screened_at?: string | null
          score?: number | null
          search_id?: string | null
          suppressed?: boolean
          suppression_reason?: string | null
          updated_at?: string
          website?: string | null
          website_need?: string
          website_quality?: string | null
          website_source?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "leads_search_id_fkey"
            columns: ["search_id"]
            isOneToOne: false
            referencedRelation: "searches"
            referencedColumns: ["id"]
          },
        ]
      }
      mail_batches: {
        Row: {
          created_at: string
          created_by: string | null
          followup_offset_days: number
          id: string
          name: string
          notes: string | null
          ordered_at: string | null
          seed_included: boolean
          seed_received_at: string | null
          sent_at: string | null
          status: string
          updated_at: string
          vendor: string
          vendor_order_id: string | null
        }
        Insert: {
          created_at?: string
          created_by?: string | null
          followup_offset_days?: number
          id?: string
          name: string
          notes?: string | null
          ordered_at?: string | null
          seed_included?: boolean
          seed_received_at?: string | null
          sent_at?: string | null
          status?: string
          updated_at?: string
          vendor?: string
          vendor_order_id?: string | null
        }
        Update: {
          created_at?: string
          created_by?: string | null
          followup_offset_days?: number
          id?: string
          name?: string
          notes?: string | null
          ordered_at?: string | null
          seed_included?: boolean
          seed_received_at?: string | null
          sent_at?: string | null
          status?: string
          updated_at?: string
          vendor?: string
          vendor_order_id?: string | null
        }
        Relationships: []
      }
      mail_scans: {
        Row: {
          device: string | null
          id: string
          ip_hash: string | null
          mail_id: string
          referrer: string | null
          scanned_at: string
          slug: string
          user_agent: string | null
        }
        Insert: {
          device?: string | null
          id?: string
          ip_hash?: string | null
          mail_id: string
          referrer?: string | null
          scanned_at?: string
          slug: string
          user_agent?: string | null
        }
        Update: {
          device?: string | null
          id?: string
          ip_hash?: string | null
          mail_id?: string
          referrer?: string | null
          scanned_at?: string
          slug?: string
          user_agent?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "mail_scans_mail_id_fkey"
            columns: ["mail_id"]
            isOneToOne: false
            referencedRelation: "lead_mail"
            referencedColumns: ["id"]
          },
        ]
      }
      scoring_criteria: {
        Row: {
          config: Json | null
          id: string
          is_active: boolean
          key: string
          label_da: string
          updated_at: string
          weight: string
        }
        Insert: {
          config?: Json | null
          id?: string
          is_active?: boolean
          key: string
          label_da: string
          updated_at?: string
          weight: string
        }
        Update: {
          config?: Json | null
          id?: string
          is_active?: boolean
          key?: string
          label_da?: string
          updated_at?: string
          weight?: string
        }
        Relationships: []
      }
      searches: {
        Row: {
          created_at: string
          created_by: string | null
          id: string
          is_archived: boolean
          name: string
          parameters: Json
          stats: Json
          status: string
          type: string
          updated_at: string
        }
        Insert: {
          created_at?: string
          created_by?: string | null
          id?: string
          is_archived?: boolean
          name: string
          parameters?: Json
          stats?: Json
          status?: string
          type?: string
          updated_at?: string
        }
        Update: {
          created_at?: string
          created_by?: string | null
          id?: string
          is_archived?: boolean
          name?: string
          parameters?: Json
          stats?: Json
          status?: string
          type?: string
          updated_at?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      mail_landing: {
        Args: { p_slug: string }
        Returns: Json
      }
      mail_opt_out: {
        Args: { p_slug: string }
        Returns: boolean
      }
      mail_track_scan: {
        Args: {
          p_slug: string
          p_user_agent?: string | null
          p_referrer?: string | null
          p_ip_hash?: string | null
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
