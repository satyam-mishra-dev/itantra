package com.nullpointers.itantra

import org.junit.Assert.assertEquals
import org.junit.Test

class CerTest {
    @Test fun exactMatchIsZero() {
        assertEquals(0.0, Cer.cer("बाढ़ का पानी", "बाढ़ का पानी"), 1e-9)
        assertEquals(0.0, Cer.wer("बाढ़ का पानी", "बाढ़ का पानी"), 1e-9)
    }

    @Test fun knownDistances() {
        assertEquals(1.0 / 3, Cer.cer("abc", "axc"), 1e-9)          // 1 sub / 3 chars
        assertEquals(0.5, Cer.wer("do not cross bridge", "do not cross the ghat"), 1e-9) // 1 ins + 1 sub / 4 words
        assertEquals(1.0, Cer.cer("", "x"), 1e-9)
        assertEquals(0.0, Cer.cer("", ""), 1e-9)
    }

    @Test fun punctuationIsNotAnError() {
        // STT never emits danda/comma; the reference has them — must score 0, like p0 norm_dev
        assertEquals(0.0, Cer.cer("बाढ़ का पानी बढ़ रहा है, तुरंत निकलें।", "बाढ़ का पानी बढ़ रहा है तुरंत निकलें"), 1e-9)
        assertEquals(0.0, Cer.wer("बाढ़ का पानी बढ़ रहा है, तुरंत निकलें।", "बाढ़ का पानी बढ़ रहा है तुरंत निकलें"), 1e-9)
    }

    @Test fun indicAgglutinationExample() {
        // one wrong akshara inside a long word: tiny CER, full-word WER hit
        val ref = "வெளியேறுங்கள்"
        val hyp = "வெளியேறுங்கல்"
        assertEquals(1.0, Cer.wer(ref, hyp), 1e-9)
        org.junit.Assert.assertTrue(Cer.cer(ref, hyp) < 0.1)
    }
}
