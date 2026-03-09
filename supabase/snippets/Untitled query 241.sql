-- Pastikan RLS nyala untuk tabel notes (seharusnya sudah nyala)
ALTER TABLE public.notes ENABLE ROW LEVEL SECURITY;

-- Buat policy untuk memperbolehkan CREATE (Insert) jika user ID sesuai
CREATE POLICY "Users can create their own notes"
ON public.notes 
FOR INSERT 
TO authenticated 
WITH CHECK (auth.uid() = user_id);
